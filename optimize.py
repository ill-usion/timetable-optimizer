import argparse
import random
import pandas as pd
from dataclasses import fields
from tabulate import tabulate
from timetable import Timetable
from heuristics import TimetableHeuristics, HeuristicsOptions
from shc_optimizer import SHCOptimizer


df = pd.read_csv("timetable.csv", index_col=0)


def parse_h_opts(args: any) -> HeuristicsOptions:
    args_dict = vars(args)
    h_keys = {f.name for f in fields(HeuristicsOptions)}
    h_dict = {k: v for k, v in args_dict.items() if k in h_keys}
    return HeuristicsOptions(**h_dict)


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
    parser.add_argument("-s", "--steps", default=10, help="Number of optimization steps", type=int)
    parser.add_argument("-tp", "--thu-penalty", default=5, help="Thursday lecture penalty", type=int)
    parser.add_argument("-mp", "--morning-penalty", default=10, help="Morning lecture penalty (08:00)", type=int)
    parser.add_argument("-cp", "--conflict-penalty", default=100, help="Lecture conflict penalty", type=int)
    parser.add_argument("-hcp", "--high-credit-penalty", default=20, help="High credit per day penalty", type=int)
    parser.add_argument("-dcl", "--daily-credit-limit", default=8, help="Maximum number of credits per day", type=int)

    args = parser.parse_args()
    h_options = parse_h_opts(args) 

    courses = args.courses
    master_table = Timetable(df)

    if not master_table.are_valid_courses(courses):
        print("Found invalid course code.")
        exit(1)

    exam_conflicts = master_table.find_exam_conflicts(courses)
    if len(exam_conflicts):
        print("The following courses contain a final exam conflict:")
        for c1, c2 in exam_conflicts:
            print(f"\t- {c1} & {c2}")

        exit(1)

    random.shuffle(courses)
    optimizer = SHCOptimizer(master_table, courses, args.steps, h_options)

    print(f"Initial table (score={optimizer.best[0]}):")
    print_timetable(optimizer.best[1])
    while optimizer.can_step():
        print("Step:", optimizer.current_step + 1)
        optimizer.step()

    print(f"Table after optimization (score={optimizer.best[0]}):")
    print_timetable(optimizer.best[1])

if __name__ == "__main__":
    main()

