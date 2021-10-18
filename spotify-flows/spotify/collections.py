"""
    This module is the main API used to create track collections
"""

# Standard library imports
from typing import List
from typing import Any
from dataclasses import dataclass, field, asdict
import random
import copy

# Third party imports
import pandas as pd

# Local imports
from spotify.playlists import get_playlist_id, get_playlist_tracks
from spotify.artists import (
    get_artist_id,
    get_artist_popular_songs,
    get_artist_albums,
    get_related_artists,
)
from spotify.albums import get_album_id, get_album_songs, get_album_info
from spotify.tracks import get_audio_features
from spotify.user import get_recommendations_for_genre, get_all_saved_tracks
from database.database import build_collection_from_id

# Main body
@dataclass
class TrackCollection:
    id_: str = ""
    _items: List[Any] = field(default_factory=list)
    _audio_features_enriched: bool = False

    # Class attributes
    read_items_from_db = lambda id_, db_path: build_collection_from_id(
        id_=id_, db_path=db_path
    )

    @property
    def items(self):
        return self._items

    @classmethod
    def from_id(cls, playlist_id: str):
        return cls(id_=playlist_id)

    @classmethod
    def from_db(cls, id_: str, db_path: str):
        items = cls.read_items_from_db(id_=id_, db_path=db_path)
        return TrackCollection(id_=id_, _items=items)

    @classmethod
    def from_name(cls, name: str):
        id_ = cls.func_get_id(name=name)
        return cls(id_=id_)

    def __str__(self):
        return "\n".join([str(item) for item in self.items])

    def __add__(self, other):
        new_items = list(set(self.items + other.items))
        enriched = (self._audio_features_enriched) and (other._audio_features_enriched)
        return TrackCollection(_items=new_items, _audio_features_enriched=enriched)

    def __radd__(self, other):
        if other == 0:
            return self
        else:
            return self + other

    def __sub__(self, other):
        new_items = list(set(self.items) - set(other.items))
        enriched = self._audio_features_enriched
        return TrackCollection(_items=new_items, _audio_features_enriched=enriched)

    def __truediv__(self, other):
        new_items = list(set(self.items).intersection(set(other.items)))
        enriched = (self._audio_features_enriched) and (other._audio_features_enriched)
        return TrackCollection(_items=new_items, _audio_features_enriched=enriched)

    def __mod__(self, other):
        current_items = self.items
        other_items = other.items

        current_items = [item for item in current_items if item not in other_items]

        new_items = [
            item
            for item_1, item_2 in zip(current_items, other_items)
            for item in (item_1, item_2)
        ]
        enriched = (self._audio_features_enriched) and (other._audio_features_enriched)
        return TrackCollection(_items=new_items, _audio_features_enriched=enriched)

    def to_dataframes(self):
        # Enrich with audio features
        self._items = self._enrich_with_audio_features(self.items)
        tracks = copy.copy(self.items)

        # Extract data
        album_artist = [
            {"album_id": track.album.id, "artist_id": artist.id}
            for track in tracks
            for artist in track.album.artists
        ]

        all_tracks = [asdict(track) for track in tracks]

        all_audio_features = [
            {"track_id": track["id"], **track["audio_features"]} for track in all_tracks
        ]

        all_albums = [asdict(track.album) for track in tracks]
        all_artists = [artist for album in all_albums for artist in album["artists"]]

        # Build dataframes
        df_all_artists = pd.DataFrame(all_artists)
        df_all_albums = pd.DataFrame(all_albums).drop(columns="artists")
        df_audio_features = pd.DataFrame(all_audio_features)

        df_all_tracks = pd.DataFrame(all_tracks)
        df_all_tracks.loc[:, "album_id"] = df_all_tracks["album"].apply(
            lambda x: x["id"]
        )

        df_all_tracks.drop(columns=["album", "audio_features"], inplace=True)
        df_album_artist = pd.DataFrame(album_artist)

        return (
            df_all_tracks,
            df_all_artists,
            df_all_albums,
            df_audio_features,
            df_album_artist,
        )

    def shuffle(self):
        new_items = copy.copy(self.items)
        random.shuffle(new_items)
        self._items = new_items
        return self

    def random(self, N: int):
        new_items = random.sample(self.items, min([N, len(self.items)]))
        self._items = new_items
        return self

    def remove_remixes(self):
        new_items = [item for item in self.items if "remix" not in item.name.lower()]
        self._items = new_items
        return self

    def sort(self, by: str, ascending: bool = True):
        str_attr = f"item.{by}"

        # Enrichment with audio features if needed
        if by.startswith("audio_features") and not self._audio_features_enriched:
            self._items = self._enrich_with_audio_features(items=self.items)
            self._audio_features_enriched = True

        sorted_items = sorted(
            self.items, key=eval(f"lambda item: {str_attr}"), reverse=(not ascending)
        )
        return TrackCollection(
            _items=sorted_items, _audio_features_enriched=self._audio_features_enriched
        )

    def filter(self, criteria: str):
        str_filter = f"item.{criteria}"

        # Enrichment with audio features if needed
        if criteria.startswith("audio_features") and not self._audio_features_enriched:
            self._items = self._enrich_with_audio_features(items=self.items)
            self._audio_features_enriched = True

        filtered_items = [item for item in self.items if eval(str_filter)]
        return TrackCollection(
            _items=filtered_items,
            _audio_features_enriched=self._audio_features_enriched,
        )

    def _enrich_with_audio_features(self, items):
        audio_features_dict = get_audio_features(
            track_ids=[track.id for track in items]
        )

        for item in items:
            item.audio_features = audio_features_dict[item.id]

        return items

    def set_id(self, id_):
        return TrackCollection(
            id_=id_,
            _items=self.items,
            _audio_features_enriched=self._audio_features_enriched,
        )

    def remove_duplicates(self):
        # By ID
        items = copy.copy(self.items)

        idx = 0
        while idx < len(items):
            names = [item.name for item in items]

            if items[idx].name in names[:idx]:
                items.pop(idx)
            else:
                idx += 1

        self._items = items
        return self


@dataclass
class Playlist(TrackCollection):
    func_get_id = lambda name: get_playlist_id(sp=None, playlist_name=name)

    @property
    def items(self):
        if self._items:
            return self._items
        else:
            return get_playlist_tracks(sp=None, playlist_id=self.id_)


class Album(TrackCollection):
    func_get_id = lambda name: get_album_id(sp=None, album_name=name)

    @property
    def items(self):
        if self._items:
            return self._items
        else:
            return get_album_songs(sp=None, album_id=self.id_)


class Artist(TrackCollection):
    func_get_id = lambda name: get_artist_id(sp=None, artist_name=name)

    @property
    def items(self):
        if self._items:
            return self._items
        else:
            return self.all_songs()

    def popular(self):
        items = get_artist_popular_songs(sp=None, artist_id=self.id_)
        return Artist(id_=self.id_, _items=items)

    def all_songs(self):
        album_data = get_artist_albums(artist_id=self.id_)
        album_collection = AlbumCollection(
            albums=[Album.from_id(album.id) for album in album_data]
        )

        if album_collection:
            track_collection = album_collection.remove_duplicates().items
        else:
            track_collection = []

        return track_collection

    def related_artists(self, n: int, include: bool = True):
        related_artists = get_related_artists(sp=None, artist_id=self.id_)

        if include:
            related_artists.append(self)
            n += 1

        return ArtistCollection(artists=related_artists[:n])


@dataclass
class ArtistCollection(TrackCollection):
    artists: List[Artist] = field(default_factory=list)

    def __post_init__(self):
        self.artists = [Artist(id_=artist.id) for artist in self.artists]

    @property
    def items(self):
        if self._items:
            return self._items
        else:
            if self.artists:
                return sum(self.artists).items
            else:
                return []

    def popular(self):
        return sum([artist.popular() for artist in self.artists])


@dataclass
class AlbumCollection(TrackCollection):
    albums: List[Artist] = field(default_factory=list)

    def __post_init__(self):
        self.albums = [Album(id_=album.id_) for album in self.albums]

    @property
    def items(self):
        if self._items:
            return self._items
        else:
            if self.albums:
                return sum(self.albums).items
            else:
                return []


class Genre(TrackCollection):
    def __init__(self, genre_name: str):
        self.genre_name = genre_name
        self._items = []

    @property
    def items(self):
        if self._items:
            return self._items
        else:
            return get_recommendations_for_genre(sp=None, genre_names=[self.genre_name])


class SavedTracks(TrackCollection):
    def __init__(self):
        self._items = []

    @property
    def items(self):
        if self._items:
            return self._items
        else:
            return get_all_saved_tracks(sp=None)
