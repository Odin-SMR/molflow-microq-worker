from datetime import timedelta


def enum(**enums):
    assert 'all_values' not in enums
    enums['all_values'] = set(value for value in enums.itervalues())
    return type('Enum', (), enums)

JOB_STATES = enum(
    available='AVAILABLE',
    claimed='CLAIMED',
    started='STARTED',
    finished='FINISHED',
    failed='FAILED')

TIME_PERIODS = enum(
    hourly='HOURLY',
    daily='DAILY',
    monthly='MONTHLY',
    yearly='YEARLY'
)

TIME_PERIOD_TO_DELTA = {
    TIME_PERIODS.yearly: timedelta(days=365),
    TIME_PERIODS.monthly: timedelta(days=365/12.),
    TIME_PERIODS.daily: timedelta(days=1),
    TIME_PERIODS.hourly: timedelta(hours=1),
}
