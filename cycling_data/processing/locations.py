from ..models.cycling_models import Location, Route

def great_circle_distance(lat1,lon1,lat2,lon2):
    """
    lat1: Latitude of first point in degrees
    lon1: Longitude of first point in degrees
    lat2: Latitude of second point in degrees
    lon2: Longitude of second point in degrees

    Returns: Great circle distance between the two points, in km.
    """
    from numpy import pi

    from sqlalchemy.sql.expression import func
    sin=func.sin
    cos=func.cos
    sqrt=func.sqrt
    arctan2=func.atan2
    power=func.power
    
    phi1=lat1*pi/180
    phi2=lat2*pi/180
    lambda1=lon1*pi/180
    lambda2=lon2*pi/180

    dlambda=lambda2-lambda1

    delta_sigma=arctan2(
        sqrt(power(cos(phi2)*sin(dlambda),2)
             +power(cos(phi1)*sin(phi2)-sin(phi1)*cos(phi2)*cos(dlambda),2)),
        sin(phi1)*sin(phi2)+cos(phi1)*cos(phi2)*cos(dlambda)
    )

    re=6371
    return delta_sigma*re
        
def get_nearby_locations(session,lat,lon,max_results=10,max_distance=50):
    distance=great_circle_distance(Location.lat,Location.lon,lat,lon)
    return session.query(Location).filter(
        distance<max_distance
    ).order_by(distance)

def get_straightline_distance(l1,l2,session):

    distance=great_circle_distance(l1.lat,l1.lon,l2.lat,l2.lon)
