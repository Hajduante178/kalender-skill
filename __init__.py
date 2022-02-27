from datetime import datetime
from logging import info
from this import d
from mycroft import MycroftSkill, intent_file_handler, intent_handler
from datetime import datetime as dt, tzinfo
from word2number import w2n
import pytz
import caldav
import icalendar
import math

Utc = pytz.UTC

class Kalender(MycroftSkill):
    '''Kalender Skill'''
    def __init__(self):
        MycroftSkill.__init__(self)

        settings_file = self.settings
        self.username = settings_file["skillMetadata"]["sections"][0]["fields"][0]["value"]
        self.password = settings_file["skillMetadata"]["sections"][0]["fields"][1]["value"]
        self.url = settings_file["skillMetadata"]["sections"][0]["fields"][2]["value"]

        info(f"USERNAME = {self.username}")
        info(f"PASSWORD = {self.password}")
        info(f"URL = {self.url}")

    def initialize(self):
        '''Initialization'''
        self.register_entity_file('year.entity')
        self.register_entity_file('month.entity')
        self.register_entity_file('day.entity')

    @intent_handler('kalender.next.event.intent')
    def handle_kalender(self, message):
        '''Intent Handler: Next event'''
        calendar = CalendarFunctions(self.url, self.username, self.password)
        event = calendar.get_next_event()
        response = get_next_event_string(event)
        self.speak_dialog(response)


    @intent_handler('kalender.events.on.day.intent')
    def handle_events_on_day(self, message):
        '''Intent Handler: Events on day'''
        month = message.data.get("month")
        day = int(message.data.get("day"))
        year = int(message.data.get("year"))

        if math.isnan(year):
            year = w2n.word_to_num(message.data.get("year"))

        if math.isnan(day):
            day = w2n.word_to_num(message.data.get("day"))

        # TO GET NUMBER OF MONTH, E.G. MARCH -> 3
        datetime_object = datetime.strptime(month, "%B")
        month_number = datetime_object.month

        calendar = CalendarFunctions(self.url, self.username, self.password)

        # CHECK IF USEABLE DATE
        if check_month(month) and check_day(day) and check_year(year):
            events = calendar.get_all_events_of_day(datetime(year, month_number, day))
            response = get_events_on_day_string(events)
            self.speak_dialog(response)
        else:
            self.speak_dialog("Date doesnt work")

    @intent_handler('kalender.create.event.intent')
    def handle_events_creation(self, message):
        day = message.data.get("day")
        month = message.data.get("month")
        year = message.data.get("year")
        start_time = message.data.get("start_time")
        end_time = message.data.get("end_time")
        title = message.data.get("test")
        calendar = CalendarFunctions(self.url, self.username, self.password)

        day_creation_start = datetime(2022, 2, 25, 0, 0, 0)
        day_creation_end = datetime(2022, 2, 25, 3, 0, 0)
        calendar.create_event(title, day_creation_start, day_creation_end)

        self.speak_dialog("Created Event")

    @intent_handler('kalender.delete.event.intent')
    def handle_events_delete(self, message):
        calendar = CalendarFunctions(self.url, self.username, self.password)
        date = datetime(2022, 2, 28, 0, 0, 0)
        event = calendar.delete_event(date)
        self.speak_dialog("Deleted appointment")

''' HELPER FUNCTIONS '''

def create_skill():
    '''Returns calendar'''
    return Kalender()

def check_month(month):
    '''
    Returns true if param != None
        Parameters:
            month: String
        Returns:
            Boolean
    '''
    if month is None:
        return False
    return True

def check_day(day):
    '''
    Check if number is a viable day
        Parameters:
            day: Number
        Returns:
            Boolean
    '''
    if day is None:
        return False
    day = int(day)
    if (day < 1) or (day > 31):
        return False
    return True

def check_year(year):
    '''
    Returns True if year is viable
        Parameters:
            year: Number
        Returns:
            Boolean
    '''
    if year is None:
        return False
    year = int(year)
    if year < 2022:
        return False
    return True


class CalendarFunctions:
    '''Contains all functions, that are needed for our calender skill'''

    calendar = None

    def __init__(self, url, calendar_username, calendar_password):
        self.client = caldav.DAVClient(
            url=url,
            username=calendar_username,
            password=calendar_password
        )
        principal = self.client.principal()
        self.calendar = principal.calendars()[0]


    def get_all_events(self):
        '''
        Gets all events from the calendar
            Parameters: None
            Returns: All events in a list
        '''
        events = self.calendar.events()
        events_to_return = []
        for event in events:
            cal = icalendar.Calendar.from_ical(event.data, True)
            url = event.url
            for vevent in cal[0].walk("vevent"):
                event_details = get_calender_events(vevent)
                event_details["event_url"] = url
                events_to_return.append(event_details)
        return events_to_return

    def ical_delete(self, events):
        """
        Parses calendar events from ical format to python dictionary
        :param events: list of events (ical strings) that should be parsed
        :return: python list containing the pared events as dictionaries
        """
        parsed_events = []
        for event in events:
            cal = icalendar.Calendar.from_ical(event.data, True)
            url = event.url
            for vevent in cal[0].walk("vevent"):
                event_details = get_calender_events(vevent)
                event_details["event_url"] = url
                parsed_events.append(event_details)
        return parsed_events

    def get_next_event(self):
        '''
        Function to get the next event from the calendar 
        (the event with the next start date in the future)
            Parameters: None
            Returns: Next event
        '''
        all_events = self.get_all_events()
        earliest_event = {}
        time_now = dt.now(tz=None)

        # loop through all events, if start time earlier -> replace earlist_event with current event
        for event in all_events:
            date_of_current_event = event["start"]
            if date_of_current_event > time_now:
                # If earliest event is empty, it will be false
                if bool(earliest_event) is False:
                    earliest_event = event
                else:
                    date_of_earliest_event = earliest_event["start"]
                    if date_of_current_event < date_of_earliest_event:
                        earliest_event = event

        return earliest_event


    def get_all_events_of_day(self, day):
        '''
        Returns all events for a given day
            Parameters: Day in datetime format
            Returns: List of events
        '''
        all_events = self.get_all_events()
        events_on_day = []

        for event in all_events:
            event_date = event["start"]
            ed = event_date
            if (ed.year == day.year) and (ed.month == day.month) and (ed.day == day.day):
                events_on_day.append(event)

        return (events_on_day, day)

    def create_event(self, event_name, begin_date, end_date):
        '''
        Create a new event in this calendar
            Parameters:
                event_name: String
                begin_date: Date in datetime format, example: datetime.datetime(2022, 2, 25, 10)) -> 25.02.2022 10:00
                end_date: Date in datetime format
            Returns: None
        '''

        helper_calendar = icalendar.Calendar()
        event = icalendar.Event()

        event.add("summary", event_name)
        event.add("dtstart", begin_date)
        event.add("dtend", end_date)

        helper_calendar.add_component(event)
        self.calendar.add_event(helper_calendar)

    def delete_event(self, date):

         start_date =  datetime.combine(date, datetime.min.time())
         end_date = datetime.combine(date, datetime.max.time())
         events = self.calendar.date_search(start=start_date, end=end_date, expand=True)
         info(events)
         event = self.ical_delete(events)
         info(event["event_url"])
         return event

def get_calender_events(cal_event):
    '''
    Build a calendar JSON Object from an event object
        Parameters: Calendar Event
        Returns: Dictionary of Events
    '''
    return {
        "summary" : str(cal_event["SUMMARY"]),
        "start" : fix_time_object(cal_event["DTSTART"].dt),
        "end" : fix_time_object(cal_event["DTEND"].dt),
        #"url" : cal_event["event_url"]
    }

def fix_time_object(time):
    '''
    Removes the timezone information, if timeobject contains timezone
        Parameters: One Datetime Object
        Returns: One Datetime Object without timezone
    '''
    try:
        hour = time.hour
    except:
        # WHEN DATE OBJECT IS ONLY DATE, NOT TIME
        time = dt(time.year, time.month, time.day)

    time = time.replace(tzinfo=None)
    return time

def get_next_event_string(event):
    """
    Takes in an event and returns a string containing the necessary information
    """
    event_name = event["summary"]
    start_time = event["start"]

    year = start_time.year
    month = start_time.strftime("%B")
    day = start_time.day

    time = start_time.strftime("%H:%M")
    return f"Your next appointment is on {month} {day}, {year} at {time} o'clock and is entitled {event_name}."

def get_events_on_day_string(events):
    '''
    Returns the events on a given day
        Parameters:
            events: List of events
        Returns:
            String: Response-String for MyCroft
    '''
    start_time = events[1]
    year = start_time.year
    month = start_time.strftime("%B")
    day = start_time.day
    return_string = f"On {month} {day}, {year} you have the following appointments: "

    # If No events on given day
    if len(events[0]) == 0:
        return f"You have no appointments on {month} {day}, {year}."

    # If only one event on day
    if len(events[0]) == 1:
        return_string = f"You have the following appointment on {month} {day}, {year}: "

    for event in events[0]:
        start_time = event["start"]
        time = start_time.strftime("%H:%M")
        event_name = event["summary"]
        event_string = f" {event_name} at {time} o'clock, "
        return_string += event_string

    return return_string[:-2] + "."
