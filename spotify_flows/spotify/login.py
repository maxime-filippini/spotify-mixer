"""
    This module holds the login routines for the Spotify API
"""

# Standard library imports
import os
from typing import Any
from typing import Callable
from functools import wraps

# Third party imports
from dotenv import load_dotenv
from spotipy.oauth2 import SpotifyOAuth

# Local imports
from .classes import ExtendedSpotify

# Main body
def login(scope: str) -> ExtendedSpotify:
    """Log in to the Spotify API

    Args:
        scope (str): Scope for the connection

    Returns:
        ExtendedSpotify: Spotify object
    """

    load_dotenv()  # Load environment variables

    sp_oauth = SpotifyOAuth(
        client_id=os.environ.get("SPOTIFY_CLIENT_ID"),
        client_secret=os.environ.get("SPOTIFY_CLIENT_SECRET"),
        redirect_uri=os.environ.get("SPOTIFY_REDIRECT_URI"),
        scope=scope,
    )

    access_token = ""
    token_info = sp_oauth.get_cached_token()

    if token_info:
        access_token = token_info["access_token"]
    else:
        auth_url = sp_oauth.get_authorize_url()
        print(auth_url)
        response = input(
            "Paste the above link into your browser, then paste the redirect url here: "
        )
        code = sp_oauth.parse_response_code(response)
        token_info = sp_oauth.get_access_token(code)
        access_token = token_info["access_token"]

    return ExtendedSpotify(auth=access_token)


def login_if_missing(scope: str) -> Callable[[Callable[[ExtendedSpotify], Any]], Any]:
    def decorator(func):
        @wraps(func)
        def wrapper(sp=None, **kwargs):
            if sp is None:
                sp = login(scope=scope)
            rv = func(sp, **kwargs)
            return rv

        return wrapper

    return decorator