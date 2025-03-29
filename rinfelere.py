import bisect as BS
import dataclasses as DC
import datetime as DT
import enum as E
import heapq as HQ
import itertools as ITR
import xml.etree.ElementTree as XML


time_zone = DT.timezone(DT.timedelta(hours=-5))
epoch = DT.datetime(2025, 3, 20, 4, 1, tzinfo=time_zone)


class OutOfCalendarBoundaries(Exception):
    pass


class Event(E.Enum):
    equinox = E.auto()
    solstice = E.auto()
    new_moon = E.auto()
    full_moon = E.auto()
    midnight = E.auto()
    noon = E.auto()
    month = E.auto()
    day = E.auto()


@DC.dataclass(eq=True, order=True, frozen=True)
class TimedEvent:
    moment: DT.datetime
    event: Event
    name: str

    def __iter__(self):
        yield self.moment
        yield self.event
        yield self.name

    def __str__(self):
        return f"[{self.moment.astimezone(None)}] {self.event.name.upper()}" \
            + f" {self.name}" if self.event == Event.day else ""


def generate_equinoxes_and_solstices():
    def names_gen():
        for year in ITR.count(1):
            for season in ITR.cycle(["Autumn", "Winter", "Spring", "Summer"]):
                yield f"{year}/{season}"
    names = names_gen()
    for year in [2025]:
        cells = XML.parse(f"seasons/{year}.xml").getroot()\
            .iterfind("./tbody/tr/td")
        events = ITR.cycle([Event.equinox, Event.solstice])
        for cell in cells:
            moment = DT.datetime.strptime(
                f"{year} {cell.text} {next(cells).text}",
                "%Y %d %b %H:%M").replace(tzinfo=time_zone)
            yield TimedEvent(moment, next(events), f"{next(names)}")


def generate_moon_phases():
    for year in [2025, 2026]:
        cells = XML.parse(f"lunar-phases/{year}.xml").getroot() \
            .iterfind("./tbody/tr/td")
        events = ITR.cycle([Event.new_moon, Event.full_moon])
        skips = 0
        for cell in cells:
            if skips:
                skips -= 1
                continue
            event = next(events)
            if cell.text is None:
                skips = 4 if event == Event.full_moon else 3
                continue
            moment = DT.datetime.strptime(
                f"{year} {cell.text} {next(cells).text}",
                "%Y %d %b %H:%M").replace(tzinfo=time_zone)
            yield TimedEvent(moment, event, "")
            skips = 3 if event == Event.full_moon else 2


def generate_daylights():
    for n in range(286):
        yield TimedEvent(epoch + DT.timedelta(days=n), Event.midnight, "")
        yield TimedEvent(epoch + DT.timedelta(days=n, hours=12), Event.noon, "")


def concialliate(major_queue, minor_queue, major_index, minor_index,
                 major_events, minor_start_event, minor_mid_event,
                 new_event, minor_pad):
    dirty_major = False
    minor_moment = None
    inherited_name = None
    for moment, event, name in HQ.merge(major_queue, minor_queue):
        if event in major_events:
            dirty_major = True
            inherited_name = name
        elif event == minor_start_event:
            minor_moment = moment
        elif event == minor_mid_event:
            if dirty_major:
                major_index += 1
                dirty_major = False
                minor_index = 1
            else:
                minor_index += 1
            if major_index:
                yield TimedEvent(minor_moment, new_event,
                 f"{inherited_name}/{str(minor_index).rjust(minor_pad, "0")}")


def generate_months():
    return concialliate(
        generate_equinoxes_and_solstices(), generate_moon_phases(),
        0, 0, [Event.equinox, Event.solstice], Event.new_moon, Event.full_moon,
        Event.month, 1)


def generate_days():
    return concialliate(
        generate_months(), generate_daylights(),
        0, 0, [Event.month], Event.midnight, Event.noon,
        Event.day, 2)


days = list(generate_days())


def convert(moment):
    index = BS.bisect(days, moment, key=lambda day: day.moment)
    if index in [0, len(days)]:
        raise OutOfCalendarBoundaries()
    sections = int((moment - days[index - 1].moment).total_seconds()
                   * 216 / 86400)
    return f"{days[index - 1].name} {str(sections).rjust(3, "0")}"


def main():
    for day in days:
        print(day)

    print("====NOW")
    print(convert(DT.datetime.now(DT.timezone.utc)))

    print("====SEASON CHANGES")
    for moment, _, _ in generate_equinoxes_and_solstices():
        try: print(convert(moment))
        except OutOfCalendarBoundaries: pass

    print("====NEW MOONS")
    for moment, event, _ in generate_moon_phases():
        if event == Event.new_moon:
            try: print(convert(moment))
            except OutOfCalendarBoundaries: pass


if __name__ == "__main__":
    main()
