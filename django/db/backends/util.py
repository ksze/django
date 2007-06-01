import datetime
from time import time
from django.utils.encoding import smart_unicode, force_unicode

try:
    import decimal
except ImportError:
    from django.utils import _decimal as decimal    # for Python 2.3

class CursorDebugWrapper(object):
    def __init__(self, cursor, db):
        self.cursor = cursor
        self.db = db

    def execute(self, sql, params=()):
        start = time()
        try:
            return self.cursor.execute(sql, params)
        finally:
            stop = time()
            self.db.queries.append({
                'sql': smart_unicode(sql) % convert_args(params),
                'time': "%.3f" % (stop - start),
            })

    def executemany(self, sql, param_list):
        start = time()
        try:
            return self.cursor.executemany(sql, param_list)
        finally:
            stop = time()
            self.db.queries.append({
                'sql': 'MANY: ' + sql + ' ' + smart_unicode(tuple(param_list)),
                'time': "%.3f" % (stop - start),
            })

    def __getattr__(self, attr):
        if attr in self.__dict__:
            return self.__dict__[attr]
        else:
            return getattr(self.cursor, attr)

def convert_args(args):
    """
    Convert sequence or dictionary to contain unicode values.
    """
    to_unicode = lambda s: force_unicode(s, strings_only=True)
    if isinstance(args, (list, tuple)):
        return tuple([to_unicode(val) for val in args])
    else:
        return dict([(to_unicode(k), to_unicode(v)) for k, v in args.items()])

###############################################
# Converters from database (string) to Python #
###############################################

def typecast_date(s):
    return s and datetime.date(*map(int, s.split('-'))) or None # returns None if s is null

def typecast_time(s): # does NOT store time zone information
    if not s: return None
    hour, minutes, seconds = s.split(':')
    if '.' in seconds: # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.time(int(hour), int(minutes), int(seconds), int(float('.'+microseconds) * 1000000))

def typecast_timestamp(s): # does NOT store time zone information
    # "2005-07-29 15:48:00.590358-05"
    # "2005-07-29 09:56:00-05"
    if not s: return None
    if not ' ' in s: return typecast_date(s)
    d, t = s.split()
    # Extract timezone information, if it exists. Currently we just throw
    # it away, but in the future we may make use of it.
    if '-' in t:
        t, tz = t.split('-', 1)
        tz = '-' + tz
    elif '+' in t:
        t, tz = t.split('+', 1)
        tz = '+' + tz
    else:
        tz = ''
    dates = d.split('-')
    times = t.split(':')
    seconds = times[2]
    if '.' in seconds: # check whether seconds have a fractional part
        seconds, microseconds = seconds.split('.')
    else:
        microseconds = '0'
    return datetime.datetime(int(dates[0]), int(dates[1]), int(dates[2]),
        int(times[0]), int(times[1]), int(seconds), int(float('.'+microseconds) * 1000000))

def typecast_boolean(s):
    if s is None: return None
    if not s: return False
    return str(s)[0].lower() == 't'

def typecast_decimal(s):
    if s is None:
        return None
    return decimal.Decimal(s)

###############################################
# Converters from Python to database (string) #
###############################################

def rev_typecast_boolean(obj, d):
    return obj and '1' or '0'

def rev_typecast_decimal(d):
    if d is None:
        return None
    return str(d)

##################################################################################
# Helper functions for dictfetch* for databases that don't natively support them #
##################################################################################

def _dict_helper(desc, row):
    "Returns a dictionary for the given cursor.description and result row."
    return dict(zip([col[0] for col in desc], row))

def dictfetchone(cursor):
    "Returns a row from the cursor as a dict"
    row = cursor.fetchone()
    if not row:
        return None
    return _dict_helper(cursor.description, row)

def dictfetchmany(cursor, number):
    "Returns a certain number of rows from a cursor as a dict"
    desc = cursor.description
    for row in cursor.fetchmany(number):
        yield _dict_helper(desc, row)

def dictfetchall(cursor):
    "Returns all rows from a cursor as a dict"
    desc = cursor.description
    for row in cursor.fetchall():
        yield _dict_helper(desc, row)
