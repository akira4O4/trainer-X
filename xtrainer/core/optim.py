from contextlib import contextmanager
from typing import Dict, Optional, List, Union

import torch
from torch.optim import Optimizer
from torch.cuda.amp import GradScaler

__all__ = [
    'OptimWrapper',
    'AMPOptimWrapper',
    'build_optimizer_wrapper',
    'build_amp_optimizer_wrapper'
]


class OptimWrapper:
    def __init__(self, optimizer: Optimizer):
        assert isinstance(optimizer, Optimizer), ('optimizer must be a `torch.optim.Optimizer` instance, but got '
                                                  f'{type(optimizer)}')
        self.optimizer = optimizer
        self._update_count = 0

    def zero_grad(self, **kwargs) -> None:
        self.optimizer.zero_grad(**kwargs)

    @property
    def param_groups(self) -> List[dict]:
        return self.optimizer.param_groups

    @property
    def lrs(self) -> list:
        # optimizer.param_groups[0]:"[‘params’, ‘lr’, ‘betas’, ‘eps’, ‘weight_decay’, ‘amsgrad’, ‘maximize’]
        lr = [group['lr'] for group in self.param_groups]
        return lr

    def state_dict(self) -> dict:
        return self.optimizer.state_dict()

    def load_state_dict(self, state_dict: dict) -> None:
        self.optimizer.load_state_dict(state_dict)

    def update(
        self,
        loss: torch.Tensor,
        loss_kwargs: Optional[Dict] = None,
        step_kwargs: Optional[Dict] = None,
        zero_kwargs: Optional[Dict] = None
    ) -> None:
        loss_kwargs = loss_kwargs or {}
        step_kwargs = step_kwargs or {}
        zero_kwargs = zero_kwargs or {}

        loss.backward(**loss_kwargs)
        self.optimizer.step(**step_kwargs)
        self.zero_grad(**zero_kwargs)
        self._update_count += 1

    @contextmanager
    def context(self):
        try:
            yield self
        finally:
            self.zero_grad()


class AMPOptimWrapper(OptimWrapper):
    def __init__(
        self,
        loss_scale: Union[str, float, Dict] = 'dynamic',
        **kwargs
    ):
        super().__init__(**kwargs)
        self._scale_update_param = None
        if loss_scale == 'dynamic':
            self.grad_scaler = GradScaler()

        elif isinstance(loss_scale, float):
            self._scale_update_param = loss_scale
            self.grad_scaler = GradScaler(init_scale=loss_scale)

        elif isinstance(loss_scale, dict):
            self.grad_scaler = GradScaler(**loss_scale)

        else:
            raise TypeError(f'loss_scale must be of type float, dict, or dynamic", but got {loss_scale}')

    def state_dict(self) -> dict:
        state_dict = self.optimizer.state_dict()
        state_dict['loss_scaler'] = self.grad_scaler.state_dict()
        return state_dict

    def load_state_dict(self, state_dict: dict) -> None:
        if 'loss_scaler' in state_dict:
            self.grad_scaler.load_state_dict(state_dict.pop('loss_scaler'))
        self.optimizer.load_state_dict(state_dict)

    def update(
        self,
        loss: torch.Tensor,
        loss_kwargs: Optional[Dict] = None,
        step_kwargs: Optional[Dict] = None,
        zero_kwargs: Optional[Dict] = None
    ) -> None:

        loss_kwargs = loss_kwargs or {}
        step_kwargs = step_kwargs or {}
        zero_kwargs = zero_kwargs or {}

        self.grad_scaler.scale(loss).backward(**loss_kwargs)
        self.grad_scaler.step(self.optimizer, **step_kwargs)
        self.grad_scaler.update()
        self.zero_grad(**zero_kwargs)

    @contextmanager
    def context(self):
        from torch.cuda.amp import autocast
        with autocast():
            yield self


def build_optimizer(name: str, **kwargs) -> Optimizer:
    optim = torch.optim.__dict__.get(name)
    assert optim is not None
    optimizer = optim(**kwargs)
    return optimizer


def build_optimizer_wrapper(name: str, **kwargs) -> OptimWrapper:
    optimizer = build_optimizer(name, **kwargs)
    optimizer_wrapper = OptimWrapper(optimizer=optimizer)
    return optimizer_wrapper


def build_amp_optimizer_wrapper(name: str, **kwargs) -> AMPOptimWrapper:
    optimizer = build_optimizer(name, **kwargs)
    amp_optimizer_wrapper = AMPOptimWrapper(optimizer=optimizer)
    return amp_optimizer_wrapper
