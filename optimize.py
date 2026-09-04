import argparse
import random
import pandas as pd
from tabulate import tabulate
from functools import cache


df = pd.read_csv("timetable.csv", index_col=0)


def are_valid_courses(courses: list[str]) -> bool:
    ''' Validates if the given courses exist in the timetable '''
    return pd.Series(courses).isin(df["Course Code"]).all()


def find_exam_conflicts(courses: list[str]) -> list[tuple[str, str]]:
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

    target_courses = df[df["Course Code"].isin(courses)]
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
    
@cache
def section_count(course: str) -> int:
    ''' Identifies the number of sections of course '''
    course_timetable = df[df["Course Code"] == course]
    count = course_timetable["Section Num"].max()
    return count


@cache
def count_courses_conflict(course1: str, course1_sec: int, course2: str, course2_sec: int) -> int:
    ''' Checks whether the two given courses conflict in timing '''
    c1_timetable = df[(df["Course Code"] == course1) & (df["Section Num"] == course1_sec)]
    c2_timetable = df[(df["Course Code"] == course2) & (df["Section Num"] == course2_sec)]
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


def count_conflicts(timetable_df: pd.DataFrame) -> int:
    ''' Counts the number of course conflicts per two lectures in the given timetable '''
    conflicts = 0
    
    tt = timetable_df[["Course Code", "Section Num"]].drop_duplicates()
    for i, r1 in tt.iterrows():
        for _, r2 in tt.loc[i + 1:].iterrows():
            conflicts += count_courses_conflict(
                r1["Course Code"], r1["Section Num"],
                r2["Course Code"], r2["Section Num"])

    return conflicts


def count_morning_lectures(timetable_df: pd.DataFrame, morning_time: int = 480) -> int:
    ''' Counts the number of morning lectures in the given timetable ''' 
    morning_lecs = timetable_df[timetable_df["From Time"] <= morning_time]

    return len(morning_lecs)


def count_consecutive_lectures(timetable: dict[str, int], time_gap: int = 10) -> int:
    pass


def count_thursday_lectures(timetable_df: pd.DataFrame) -> int:
    ''' Counts the number of lectures that occur on Thursday '''
    thursday_lecs = timetable_df[timetable_df["Day"] == "THU"]
    
    return len(thursday_lecs)

def count_credits_per_day(timetable_df: pd.DataFrame):
    ''' Groups by day of the week and counts the number of credits per day '''
    lecs_by_dow = timetable_df.groupby("Day")

    return lecs_by_dow.agg({"Credits": "sum"}, axis=0)


def rand_timetable(courses: list[str]):
    ''' Picks random sections of the given courses without checking for conflicts '''
    table = dict()
    for course in courses:
        count = section_count(course)
        rand_sec = random.randint(1, count)
        table[course] = rand_sec

    return table


def neighbors(timetable: dict[str, int]):
    ''' Generates neighboring timetables to the given one '''
    for course, section in timetable.items():
        for i in range(1, section_count(course) + 1):
            if section == i:
                continue
           
            clone = timetable.copy()
            clone[course] = i
            yield clone


def score(timetable: dict[str, int], penalties: any) -> float:
    ''' Scores a timetable based on conflict and timing criteria '''
    timetable_df = df[(df[["Course Code", "Section Num"]].apply(tuple, axis=1).isin(timetable.items()))] 

    CONFLICT_PENALTY = penalties.conflict_penalty
    THURSDAY_PENALTY = penalties.thu_penalty
    MORNING_PENALTY = penalties.morning_penalty
    HIGH_CREDIT_PENALTY = penalties.high_credit_penalty
    CREDIT_PER_DAY_LIMIT = penalties.daily_credit_limit

    s = 0
    
    conflicts = count_conflicts(timetable_df)
    morning_lecs = count_morning_lectures(timetable_df)
    thursday_lecs = count_thursday_lectures(timetable_df)
    credits_per_dow = count_credits_per_day(timetable_df)
    credit_limited_days = len(credits_per_dow[credits_per_dow["Credits"] > CREDIT_PER_DAY_LIMIT])

    s += conflicts * CONFLICT_PENALTY
    s += morning_lecs * MORNING_PENALTY
    s += thursday_lecs * THURSDAY_PENALTY
    s += credit_limited_days * HIGH_CREDIT_PENALTY

    fmt_courses = f"[{', '.join(f'{c}={s:02d}' for c, s in timetable.items())}]"
    print(fmt_courses, "Score:", s, "Conflicts:", conflicts, "Morning lectures:", morning_lecs, "Thursday lectures:", thursday_lecs, "High credit days:", credit_limited_days)
    return s


def print_timetable(timetable: dict[str, int]) -> None:
    all_lecs = df[df[["Course Code", "Section Num"]].apply(tuple, axis=1).isin(timetable.items())]

    def fmt_time(m):
        h, m = divmod(m, 60)
        return f"{h:02d}:{m:02d}"

    def filter(day, from_time, to_time):
        return all_lecs[(all_lecs["Day"] == day) & \
                (all_lecs["From Time"] == from_time) & \
                (all_lecs["To Time"] == to_time)]


    time_pairs = tuple()
    # TODO: vectorize?
    for course, section in timetable.items():
        course_timetable = all_lecs[(all_lecs["Course Code"] == course) & (all_lecs["Section Num"] == section)]
        from_times = course_timetable["From Time"].to_list()    
        to_times = course_timetable["To Time"].to_list()    
        time_pairs += tuple(zip(from_times, to_times))
    time_pairs = tuple(sorted(set(time_pairs), key=sum))

    days = ("SUN", "MON", "TUE", "WED", "THU")
    headers = ("Time / Day",) + days
    table = []
    for tp in time_pairs:
        row = [f"{fmt_time(tp[0])}-{fmt_time(tp[1])}"]
        for day in days:
            filtered = filter(day, tp[0], tp[1])
            lectures = filtered["Course Code"].to_list()
            sections = filtered["Section Num"].to_list()
            halls = filtered["Hall"].to_list()

            formatted = "\n".join(f"{l}({s})@{h}" for l, s, h in zip(lectures, sections, halls))
            row.append(formatted)

        table.append(row)

    print(tabulate(table, headers=headers, tablefmt="rounded_grid", headersglobalalign="center"))
        

def main():
    parser = argparse.ArgumentParser(description="Program that finds the most optimal timetable")
    parser.add_argument("courses", nargs="+", help="Selected courses")
    parser.add_argument("-tp", "--thu-penalty", default=5, help="Thursday lecture penalty", type=int)
    parser.add_argument("-mp", "--morning-penalty", default=10, help="Morning lecture penalty (08:00)", type=int)
    parser.add_argument("-cp", "--conflict-penalty", default=100, help="Lecture conflict penalty", type=int)
    parser.add_argument("-hcp", "--high-credit-penalty", default=20, help="High credit per day penalty", type=int)
    parser.add_argument("-dcl", "--daily-credit-limit", default=8, help="Maximum number of credits per day", type=int)

    args = parser.parse_args()
    courses = args.courses

    if not are_valid_courses(courses):
        print("Found invalid course code.")
        exit(1)

    exam_conflicts = find_exam_conflicts(courses)
    if len(exam_conflicts):
        print("The following courses contain a final exam conflict:")
        for c1, c2 in exam_conflicts:
            print(f"\t- {c1} & {c2}")

        exit(1)

    random.shuffle(courses)
    table = rand_timetable(courses)

    STEPS = 50
    best = (score(table, args), table)
    
    print(f"INITIAL RANDOM TABLE (Score={best[0]}):")
    print_timetable(table)

    for _ in range(STEPS):
        cur_best = None
        for neighbor in neighbors(table):
            new_h = score(neighbor, args)
            if (cur_best is not None and cur_best[0] > new_h) or (new_h < best[0]):
                cur_best = (new_h, neighbor)
                if new_h == 0:
                    break
        
        if cur_best is None:
            table = rand_timetable(courses)
            continue
        
        best = cur_best
        if best[0] == 0:
            break

    print()
    score(best[1], args)
    print(f"AFTER OPTIMIZATION(Score={best[0]}):")
    print_timetable(best[1])


if __name__ == "__main__":
    main()

