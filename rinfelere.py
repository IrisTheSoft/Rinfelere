import dataclasses as DC
import datetime as DT
import enum as E
import heapq as HQ
import itertools as ITR
import xml.etree.ElementTree as XML


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
        name = f" {self.name}" if self.event == Event.day else ""
        return f"[{self.moment}] {self.event.name.upper()}{name}"


ref_tz = DT.timedelta(hours=-5)
epoch = DT.datetime(2025, 3, 20, 4, 1) - ref_tz


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
            yield TimedEvent(DT.datetime.strptime(
                f"{year} {cell.text} {next(cells).text}",
                "%Y %d %b %H:%M"
            ) - ref_tz, next(events), f"{next(names)}")


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
            yield TimedEvent(DT.datetime.strptime(
                f"{year} {cell.text} {next(cells).text}",
                "%Y %d %b %H:%M"
            ) - ref_tz, event, "")
            skips = 3 if event == Event.full_moon else 2


def generate_daylights():
    for n in range(286):
        yield TimedEvent(epoch + DT.timedelta(days=n), Event.midnight, "")
        yield TimedEvent(epoch + DT.timedelta(days=n, hours=12), Event.noon, "")


def concialliate(major_queue, minor_queue, major_index, minor_index,
                 major_events, minor_start_event, minor_mid_event,
                 new_event):
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
                    f"{inherited_name}/{minor_index}")


def generate_months():
    return concialliate(
        generate_equinoxes_and_solstices(), generate_moon_phases(),
        0, 0, [Event.equinox, Event.solstice], Event.new_moon, Event.full_moon,
        Event.month)


def generate_days():
    return concialliate(
        generate_months(), generate_daylights(),
        0, 0, [Event.month], Event.midnight, Event.noon,
        Event.day)


def main():
    for day in generate_days():
        print(day)


if __name__ == "__main__":
    main()
