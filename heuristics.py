import pandas as pd 
from dataclasses import dataclass


@dataclass
class HeuristicsOptions:
    thu_penalty: int
    morning_penalty: int
    conflict_penalty: int
    high_credit_penalty: int
    daily_credit_limit: int


class TimetableHeuristics:
    def __init__(self, timetable: pd.DataFrame, args: HeurisitcsOptions):
        ''' Initializes a heuristics object with the given timetable and course selection '''
        self.timetable_df = timetable
        self.args = args
        self.val = None

    
    def count_courses_conflict(self, course1: str, course1_sec: int, course2: str, course2_sec: int) -> int:
        ''' Checks whether the two given courses conflict in timing '''
        c1_timetable = self.timetable_df[(self.timetable_df["Course Code"] == course1) & (self.timetable_df["Section Num"] == course1_sec)]
        c2_timetable = self.timetable_df[(self.timetable_df["Course Code"] == course2) & (self.timetable_df["Section Num"] == course2_sec)]
        count = 0

        # TODO: vectorize
        for i1, row1 in c1_timetable.iterrows():
            for i2, row2 in c2_timetable.iterrows():
                if (row1["Day"] == row2["Day"]) and \
                    (
                        (row1["From Time"] == row2["From Time"] and row1["To Time"] == row2["To Time"]) or \
                        (row1["From Time"] >= row2["From Time"] and row1["From Time"] <= row2["To Time"]) or \
                        (row1["To Time"] >= row2["From Time"] and row1["To Time"] <= row2["To Time"]) \
                    ):
                    count += 1

        return count
    
    def count_conflicts(self) -> int:
        ''' Counts the number of course conflicts per two lectures in the given timetable '''
        conflicts = 0
        
        tt = self.timetable_df[["Course Code", "Section Num"]].drop_duplicates()
        for i, r1 in tt.iterrows():
            for _, r2 in tt.loc[i + 1:].iterrows():
                conflicts += self.count_courses_conflict(
                    r1["Course Code"], r1["Section Num"],
                    r2["Course Code"], r2["Section Num"])

        return conflicts

    def count_morning_lectures(self, morning_time: int = 480) -> int:
        ''' Counts the number of morning lectures in the given timetable ''' 
        morning_lecs = self.timetable_df[self.timetable_df["From Time"] <= morning_time]

        return len(morning_lecs)


    def count_consecutive_lectures(self, time_gap: int = 10) -> int:
        pass


    def count_thursday_lectures(self) -> int:
        ''' Counts the number of lectures that occur on Thursday '''
        thursday_lecs = self.timetable_df[self.timetable_df["Day"] == "THU"]
        
        return len(thursday_lecs)

    def count_credits_per_day(self):
        ''' Groups by day of the week and counts the number of credits per day '''
        lecs_by_dow = self.timetable_df.groupby("Day")

        return lecs_by_dow.agg({"Credits": "sum"}, axis=0)


    # TODO: Heuristics options object
    def score(self) -> float:
        ''' Scores a timetable based on conflict and timing criteria '''
        if self.val is not None:
            return self.val

        CONFLICT_PENALTY = self.args.conflict_penalty
        THURSDAY_PENALTY = self.args.thu_penalty
        MORNING_PENALTY = self.args.morning_penalty
        HIGH_CREDIT_PENALTY = self.args.high_credit_penalty
        CREDIT_PER_DAY_LIMIT = self.args.daily_credit_limit

        s = 0
        
        conflicts = self.count_conflicts()
        morning_lecs = self.count_morning_lectures()
        thursday_lecs = self.count_thursday_lectures()
        credits_per_dow = self.count_credits_per_day()
        credit_limited_days = len(credits_per_dow[credits_per_dow["Credits"] > CREDIT_PER_DAY_LIMIT])

        s += conflicts * CONFLICT_PENALTY
        s += morning_lecs * MORNING_PENALTY
        s += thursday_lecs * THURSDAY_PENALTY
        s += credit_limited_days * HIGH_CREDIT_PENALTY

        course_sec_pair = self.timetable_df[["Course Code", "Section Num"]].drop_duplicates()
        fmt_courses = f"[{', '.join(f'{c}={s:02d}' for c, s in course_sec_pair.itertuples(index=False))}]"
        print(fmt_courses, "Score:", s, "Conflicts:", conflicts, "Morning lectures:", morning_lecs, "Thursday lectures:", thursday_lecs, "High credit days:", credit_limited_days)

        self.val = s
        return s


    def __eq__(self, other: any):
        if isinstance(other, int):
            return self.score() == other

        if isinstance(other, TimetableHeuristics):
            return self.score() == other.score()

        raise ValueError("Invalid `other` type")

    def __lt__(self, other: any):
        if isinstance(other, int):
            return self.score() < other

        if isinstance(other, TimetableHeuristics):
            return self.score() < other.score()

        raise ValueError("Invalid `other` type")

    def __gt__(self, other: any):
        if isinstance(other, int):
            return self.score() > other

        if isinstance(other, TimetableHeuristics):
            return self.score() > other.score()

        raise ValueError("Invalid `other` type")

    def __le__(self, other: any):
        if isinstance(other, int):
            return self.score() <= other

        if isinstance(other, TimetableHeuristics):
            return self.score() <= other.score()

        raise ValueError("Invalid `other` type")

    def __ge__(self, other: any):
        if isinstance(other, int):
            return self.score() >= other

        if isinstance(other, TimetableHeuristics):
            return self.score() >= other.score()

        raise ValueError("Invalid `other` type")

    def __repr__(self):
        return str(self.score())
