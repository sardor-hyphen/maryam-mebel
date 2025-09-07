"""Utility functions for the application"""

def average_rating(ratings):
    """Calculate average rating from list of ratings"""
    if not ratings:
        return 0.0
    
    total = sum(rating.get('rating', 0) for rating in ratings)
    return round(total / len(ratings), 1)


def init_app(app):
    """Register utility functions with the app"""
    app.jinja_env.filters['average_rating'] = average_rating
    