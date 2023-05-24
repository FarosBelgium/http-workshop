import datetime


class HttpDate:

    def __init__(self):
        self.__months = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"]
        self.__week_days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]

    # Returns the current date and time in the correct format as it should be shown in the http headers
    @staticmethod
    def now() -> str:
        return HttpDate().__now()

    # Parses the given date to a datetime-object
    @staticmethod
    def parse(date_from_request: str) -> datetime:
        return HttpDate().__parse(date_from_request)

    # Determines whether the first given date is after the second given date
    @staticmethod
    def is_after(date1_from_request: str, date2_from_request: str) -> bool:
        given_date1: datetime = HttpDate().__parse(date1_from_request)
        given_date2: datetime = HttpDate().__parse(date2_from_request)
        return given_date1 > given_date2

    # Creates the date and time that corresponds to the given timestamp in the correct format as it should be shown
    # in the http headers
    @staticmethod
    def get_http_date_from_timestamp(timestamp: float) -> str:
        date: datetime = datetime.datetime.utcfromtimestamp(timestamp)
        return HttpDate().__given_time(date.year, date.month, date.day, date.weekday(), date.hour, date.minute,
                                       date.second)

    def __given_time(self, year: int, month: int, day: int, weekday: int, hours: int, minutes: int,
                     seconds: int) -> str:
        month = self.__months[month - 1]
        week_day = self.__week_days[weekday]
        hours = str(hours).zfill(2)
        minutes = str(minutes).zfill(2)
        seconds = str(seconds).zfill(2)

        return f"{week_day}, {day} {month} {year} {hours}:{minutes}:{seconds} GMT"

    def __now(self) -> str:
        date = datetime.datetime.now(tz=datetime.timezone.utc)
        return self.__given_time(date.year, date.month, date.day, date.weekday(), date.hour, date.minute, date.second)

    def __parse(self, date_from_request: str) -> datetime:
        date_from_request = date_from_request.strip()
        _week_day, day, month, year, time, _gmt = date_from_request.split(" ")
        month = int(self.__months.index(month) + 1)
        day = int(day)
        year = int(year)
        hours, minutes, seconds = time.split(":")
        hours = int(hours)
        minutes = int(minutes)
        seconds = int(seconds)

        return datetime.datetime(year=year, month=month, day=day, hour=hours, minute=minutes,
                                 second=seconds)
