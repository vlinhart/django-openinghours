# -*- coding: utf-8 -*-
from __future__ import unicode_literals
from django.template import Library, Context
from django.template.loader import get_template
from django.utils.translation import ugettext_lazy as _

from openinghours.models import WEEKDAYS, OpeningHours
from openinghours import utils


register = Library()


@register.filter(expects_localtime=True)
def iso_day_to_weekday(d):
    """
    Returns the weekday's name given a ISO weekday number;
    "today" if today is the same weekday.
    """
    if int(d) == utils.get_now().isoweekday():
        return _("today")
    for w in WEEKDAYS:
        if w[0] == int(d):
            return w[1]


@register.filter(expects_localtime=True)
def to_weekday(date_obj_tpl):
    oh, date_obj = date_obj_tpl
    now = utils.get_now()
    day = date_obj.isoweekday()
    if day == now.isoweekday() and (date_obj - now).days == 0:
        return _("today")
    for w in WEEKDAYS:
        if w[0] == int(day):
            return w[1]


@register.assignment_tag
def is_open(location=None, attr=None):
    """
    Returns False if the location is closed, or the OpeningHours object
    to show the location is currently open.
    """
    obj = utils.is_open(location)
    if obj is False:
        return False
    if attr is not None:
        return getattr(obj, attr)
    return obj


@register.assignment_tag
def next_time_open(location):
    """
    Returns the next possible OpeningHours object, or False
    if the location is currently open or if there is no such object.
    """
    obj, ts = utils.next_time_open(location)
    return obj


@register.filter(expects_localtime=True)
def has_closing_rule_for_now(location, attr=None):
    obj = utils.has_closing_rule_for_now(location)
    if obj is False:
        return False
    if attr is not None:
        return getattr(obj, attr)
    return obj


@register.filter(expects_localtime=True)
def get_closing_rule_for_now(location, attr=None):
    obj = utils.get_closing_rule_for_now(location)
    if obj is False:
        return False
    if attr is not None:
        return getattr(obj[0], attr)
    return obj


def dayname_transform(dayname):
    return dayname[:2].title()


@register.simple_tag
def opening_hours(location, concise=True):
    """
    Creates a rendered listing of hours.
    """
    template_name = 'openinghours/opening_hours_list.html'
    days = []  # [{'hours': '9:00am to 5:00pm', 'name': u'Monday'}, {'hours...

    ohrs = OpeningHours.objects.filter(company=location)
    if not ohrs.exists():
        return ''

    ohrs.order_by('weekday', 'from_hour')

    for o in ohrs:
        days.append({
            'day_number': o.weekday,
            'name': dayname_transform(o.get_weekday_display()),
            'from_hour': o.from_hour,
            'to_hour': o.to_hour,
            'hours': ['%s-%s' % (
                o.from_hour.strftime('%H:%M'),
                o.to_hour.strftime('%H:%M'),
            )]
        })

    open_days = [o.weekday for o in ohrs]
    for day_number, day_name in WEEKDAYS:
        if day_number not in open_days:
            days.append({
                'day_number': day_number,
                'name': dayname_transform(day_name),
                'hours': [_('Zavřeno')]
            })
    days = sorted(days, key=lambda k: k['day_number'])

    groupped_days = {}
    for day in days:
        if day['day_number'] in groupped_days:
            groupped_days[day['day_number']]['hours'].extend(day['hours'])
        else:
            groupped_days[day['day_number']] = day
    days = [groupped_days[day_number] for day_number in sorted(groupped_days.keys())]

    if concise:
        # [{'hours': '9:00am to 5:00pm', 'day_names': u'Monday to Friday'},
        #  {'hours':...
        template_name = 'openinghours/opening_hours_list_concise.html'
        concise_days = []
        current_set = {}
        for day in days:
            if 'hours' not in current_set.keys():
                current_set = {'day_names': [day['name']],
                               'hours': day['hours']}
            elif day['hours'] != current_set['hours']:
                concise_days.append(current_set)
                current_set = {'day_names': [day['name']],
                               'hours': day['hours']}
            else:
                current_set['day_names'].append(day['name'])
        concise_days.append(current_set)

        for day_set in concise_days:
            if len(day_set['day_names']) > 1:
                day_set['day_names'] = '%s-%s' % (day_set['day_names'][0],
                                                  day_set['day_names'][-1])
            else:
                day_set['day_names'] = '%s' % day_set['day_names'][0]

        days = concise_days

    template = get_template(template_name)
    return template.render(Context({'days': days}))
