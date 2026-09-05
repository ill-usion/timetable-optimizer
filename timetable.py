import random
import pandas as pd
from tabulate import tabulate
from functools import lru_cache


class Timetable:
    def __init__(self, timetable_df: pd.DataFrame):
        self.df = timetable_df


    def are_valid_courses(self, courses: list[str]) -> bool:
        ''' Validates if the given courses exist in the timetable '''
        return pd.Series(courses).isin(self.df["Course Code"]).all()


    def find_exam_conflicts(self, courses: list[str]) -> list[tuple[str, str]]:
        ''' Finds final exam conflicts by date and time '''
        def parse_date(row):
            epoch, duration = row["Exam Date/Time"].split("+")
            epoch = int(epoch)
            duration = int(duration) // 60

            dt = pd.to_datetime(epoch, unit="s") + pd.Timedelta("4h") # TODO: find better fix
            row["Date"] = dt.date()
            row["From"] = dt.time()
            row["To"] = (dt + pd.Timedelta(duration, "m")).time()
            # h, m = divmod(duration, 60)
            # row["Duration"] = f"{h:02d}:{m:02d}"

            return row

        def conflicts(from1, to1, from2, to2) -> bool:
            latest_start = max(from1, from2)
            earliest_end = min(to1, to2)

            return latest_start <= earliest_end

        target_courses = self.df[self.df["Course Code"].isin(courses)]
        exam_times = target_courses[["Course Code", "Exam Date/Time"]].dropna().drop_duplicates()
        exam_times = exam_times.apply(parse_date, axis=1)

        gb_date = exam_times.groupby("Date")
        # print(gb_date.apply(lambda x: x[:]))

        # TODO: vectorize
        exam_conflicts = []
        for date, exams in gb_date:
            if len(exams) < 2:
                continue

            for i, e1 in exams.iterrows():
                for _, e2 in exams.loc[i + 1:].iterrows():
                    if conflicts(e1["From"], e1["To"], e2["From"], e2["To"]):
                        exam_conflicts.append((e1["Course Code"], e2["Course Code"]))

        return exam_conflicts


    @lru_cache(maxsize=256)
    def section_count(self, course: str) -> int:
        ''' Identifies the number of sections of course '''
        course_timetable = self.df[self.df["Course Code"] == course]
        count = course_timetable["Section Num"].max()
        return count


    def random(self, courses: list[str]) -> dict[str, int]:
        ''' Picks random sections of the given courses without checking for conflicts '''
        table = dict()
        for course in courses:
            count = self.section_count(course)
            rand_sec = random.randint(1, count)
            table[course] = rand_sec

        return table


    def neighbors(self, timetable: dict[str, int]) -> dict[str, int]:
        ''' Generates neighboring timetables to the given one '''
        for course, section in timetable.items():
            for i in range(1, self.section_count(course) + 1):
                if section == i:
                    continue
               
                clone = timetable.copy()
                clone[course] = i
                yield clone


    def filter(self, course_selection: dict[str, int]) -> pd.DataFrame:
        return self.df[self.df[["Course Code", "Section Num"]].apply(tuple, axis=1).isin(course_selection.items())]
