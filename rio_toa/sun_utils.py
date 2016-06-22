import re
import datetime
import numpy as np


def parse_utc_string(collected_date, collected_time_utc):
    """
    Given a string in the format:
        YYYY-MM-DD HH:MM:SS.SSSSSSSSZ
    Parse and convert into a datetime object

    Parameters
    -----------
    collected_date_utc: str
        Format: YYYY-MM-DD 
    collected_time: str
        Format: HH:MM:SS.SSSSSSSSZ

    Returns
    --------
    datetime object
        parsed scene center time
    """
    utcstr = collected_date + ' ' + collected_time_utc

    if not re.match(r'[0-9]{4}\-[0-9]{2}\-[0-9]{2}\ [0-9]{2}\:[0-9]{2}\:[0-9]{2}\.[0-9]+Z', utcstr):
        raise ValueError("%s is an invalid utc time" % utcstr)

    return datetime.datetime.strptime(
        utcstr.split(".")[0],
        "%Y-%m-%d %H:%M:%S")


def time_to_dec_hour(parsedtime):
    """
    Calculate the decimal hour from a datetime object

    Parameters
    -----------
    parsedtime: datetime object

    Returns
    --------
    decimal hour: float
        time in decimal hours
    """
    return (parsedtime.hour +
            (parsedtime.minute / 60.0) +
            (parsedtime.second / 60.0 ** 2)
            )


def calculate_declination(d, lat):
    """
    Calculate the declination of the sun in degrees based on a given day
    See: https://en.wikipedia.org/wiki/Position_of_the_Sun#Calculations

    Parameters
    -----------
    d: int
        days from midnight on January 1st

    Returns
    --------
    declination in radians: float
        the declination on day 

    """
    return (np.arcsin(0.39799 * np.cos(
                np.deg2rad(0.98565) *
                (d + 10) +
                np.deg2rad(1.914) *
                np.sin(np.deg2rad(0.98565) * (d - 2)))) *
            (((np.mean(lat) > 0) + 1) * 2 - 3))


def solar_angle(utc_hour, longitude):
    """
    Given a utc decimal hour and longitudes, compute the solar angle
    for these longitudes

    Parameters
    -----------
    utc_hour: float
        decimal hour of the day in utc time to compute solar angle for
    longitude: ndarray or float
        longitude of the point(s) to compute solar angle for

    Returns
    --------
    solar angle in degrees for these longitudes
    """
    localtime = (longitude / 180.0) * 12 + utc_hour

    return ((localtime - 12.0) * (360.0 / 24.0))


def _calculate_sun_elevation(longitude, latitude, declination, utc_hour):
    """
    Calculates the solar elevation angle
    https://en.wikipedia.org/wiki/Solar_zenith_angle

    Parameters
    -----------
    longitude: ndarray or float
        longitudes of the point(s) to compute solar angle for
    latitude: ndarray or float
        latitudes of the point(s) to compute solar angle for
    declination: float
        declination of the sun in radians
    utc_hour: float
        decimal hour from a datetime object

    Returns
    --------
    the solar elevation angle in degrees
    """
    hour_angle = solar_angle(utc_hour, longitude)

    return 90 - np.rad2deg(
            np.arcsin(
                (np.sin(np.deg2rad(latitude)) *
                np.sin(declination)) +
                (np.cos(np.deg2rad(latitude)) *
                np.cos(declination) *
                np.cos(np.deg2rad(hour_angle)))
                )
            )


def sun_elevation(bounds, shape, date_collected, time_collected_utc):
    """
    Given a raster's bounds + dimensions, calculate the
    sun elevation angle in degrees for each input pixel
    based on metadata from a Landsat MTL file

    Parameters
    -----------
    bounds: BoundingBox
        bounding box of the input raster
    shape: tuple
        tuple of (rows, cols) or (depth, rows, cols) for input raster
    collected_date_utc: str
        Format: YYYY-MM-DD 
    collected_time: str
        Format: HH:MM:SS.SSSSSSSSZ

    Returns
    --------
    ndarray
        ndarray with shape = (rows, cols) with sun elevation
        in degrees calculated for each pixel
    """
    utc_time = parse_utc_string(date_collected, time_collected_utc)

    if len(shape) == 3:
        _, rows, cols = shape
    else:
        rows, cols = shape

    xCell = (bounds.right - bounds.left) / float(cols)
    yCell = (bounds.top - bounds.bottom) / float(rows)

    lat, lng = np.indices((rows, cols))

    lng = (lng.astype(np.float32) * xCell) + bounds.left + (xCell / 2.0)
    lat = (lat.astype(np.float32) * yCell) + bounds.bottom + (yCell / 2.0)

    decimal_hour = time_to_dec_hour(utc_time)
    solar_hour_angle = solar_angle(decimal_hour, lng)
    declination = calculate_declination(utc_time.timetuple().tm_yday, lat)

    return _calculate_sun_elevation(lng, lat, declination, decimal_hour)