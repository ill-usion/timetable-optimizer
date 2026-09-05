import pandas as pd
from timetable import Timetable
from optimizer import HeuristicOptimizer
from heuristics import TimetableHeuristics, HeuristicsOptions


class SHCOptimizer(HeuristicOptimizer):
    def __init__(self, timetable: Timetable, courses: list[str], max_steps: int, h_opts: HeuristicsOptions):
        super().__init__(max_steps)
        self.timetable = timetable
        self.courses = courses
        self.h_opts = h_opts

        _table = self.timetable.random(self.courses)
        _heuristics = TimetableHeuristics(self.timetable.filter(_table), self.h_opts)
        self.best = (_heuristics, _table)


    def step(self):
        current_best = None
        self.current_step += 1

        for neighbor in self.timetable.neighbors(self.best[1]):
            neighbor_h = TimetableHeuristics(self.timetable.filter(neighbor), self.h_opts)
            if neighbor_h < self.best[0]:
                current_best = (neighbor_h, neighbor)
                self.best = current_best
                return 

        if current_best is None:
            self.reached_optimum = True


