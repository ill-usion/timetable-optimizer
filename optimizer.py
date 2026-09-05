from abc import ABC, abstractmethod


class HeuristicOptimizer(ABC):
    def __init__(self, max_steps: int):
        self.current_step = 0
        self.max_steps = max_steps
        self.reached_optimum = False
        self.best = None

    @abstractmethod
    def step(self):
        pass

    def can_step(self) -> bool:
        return (not self.reached_optimum) or (self.current_step < self.max_steps) 

