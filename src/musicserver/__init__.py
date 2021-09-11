#!/usr/bin/env python

'''Entry point to the music server.'''

import collections
import hashlib
import json
import logging
import os

import gi
gi.require_version('Gst', '1.0')
from gi.repository import Gst
import tornado.gen
import tornado.ioloop

import musicserver.utils.web as web

__author__ = 'Antonio Serrano Hernandez'
__copyright__ = 'Copyright 2021'
__license__ = 'proprietary'
__version__ = '0.1'
__maintainer__ = 'Antonio Serrano Hernandez'
__email__ = 'toni.serranoh@gmail.com'
__status__ = 'Development'


############################### Web interface #################################

DEFAULT_PORT = 8888
DEFAULT_SONGDIR = '/var/lib/musicserver/songs'
DEFAULT_PLAYLIST_SIZE = 10
DEFAULT_EVENT_WAIT_TIME = 0.1

class Application:
    '''Music server main application.'''

    def __init__(self, configuration=None):
        self._load_configuration(configuration)
        self._setup_logger()
        self._setup_musicserver()
        self._start_webserver()

    def _load_configuration(self, configuration):
        '''Load the configuration from the json file.'''
        if configuration is not None:
            with open(configuration, 'r') as f:
                self._configuration = json.loads(f.read())
        else:
            # By default, load an empty configuration
            self._configuration = {}

    def _setup_logger(self):
        '''Setup the logger.'''
        logging_args = {
            'format': '%(asctime)s: %(levelname)s: %(message)s',
            'datefmt': '%b %d %H:%M:%S'
        }
        try:
            logfile = self._configuration['general']['logfile']
            logging_args['filename'] = logfile
        except KeyError: pass
        try:
            logging_args['level'] = self._configuration['general']['loglevel']
        except KeyError: pass
        logging.basicConfig(**logging_args)

    def _setup_musicserver(self):
        '''Setup the Music Server.'''
        self._musicserver = MusicServer(self._configuration)

    def _start_webserver(self):
        '''Start the web interface.'''
        try:
            port = self._configuration['webserver']['port']
        except KeyError:
            port = DEFAULT_PORT
        self._webserver = web.WebServer([], port=port)
        self._service = web.WebService(
            'musicserver', self._webserver, data=self._musicserver)

        # Add the methods to the web service
        self._service.addmethods([
            ('clear', ClearMethod, web.WebService.GET),
            ('enqueue', EnqueueMethod, web.WebService.POST),
            ('next', NextMethod, web.WebService.GET),
            ('pause', PauseMethod, web.WebService.GET),
            ('play', PlayMethod, web.WebService.GET),
            ('prev', PrevMethod, web.WebService.GET),
            ('remove', RemoveMethod, web.WebService.GET),
            ('seek', SeekMethod, web.WebService.GET),
            ('setvolume', SetvolumeMethod, web.WebService.GET),
            ('skipbackwards', SkipbackwardsMethod, web.WebService.GET),
            ('skipforwards', SkipforwardsMethod, web.WebService.GET),
            ('status', StatusMethod, web.WebService.GET),
            ('stop', StopMethod, web.WebService.GET),
        ])

    def run(self):
        '''Run the main application.'''
        logging.info('starting')
        self._webserver.run()
        logging.info('exiting')

    def stop(self):
        self._webserver.stop()
        self._musicserver.close()

    def ready(self):
        '''Return whether the server is ready or not.'''
        return self._webserver.ready()

class ClearMethod(web.WebServiceMethod):
    '''Web Service clear method.'''

    async def execute(self):
        '''Remove all songs from the playlist.'''
        self.data.clear()

class EnqueueMethod(web.WebServiceMethod):
    '''Web Service enqueue method.'''

    async def execute(self, title):
        '''Enqueue a song to the playlist.'''
        self.data.enqueue(title, self.request.body)

class NextMethod(web.WebServiceMethod):
    '''Web Service next method.'''

    async def execute(self):
        '''Go to the next song in the playlist.'''
        self.data.next()

class PauseMethod(web.WebServiceMethod):
    '''Web Service pause method.'''

    async def execute(self):
        '''Set the player to pause.'''
        self.data.pause()

class PlayMethod(web.WebServiceMethod):
    '''Web Service play method.'''

    async def execute(self):
        '''Set the player to play.'''
        self.data.play()

class PrevMethod(web.WebServiceMethod):
    '''Web Service prev method.'''

    async def execute(self):
        '''Go to the previous song in the playlist.'''
        self.data.prev()

class RemoveMethod(web.WebServiceMethod):
    '''Web Service remove method.'''

    async def execute(self, index):
        '''Remove a song the playlist.'''
        self.data.remove(int(index))

class SeekMethod(web.WebServiceMethod):
    '''Web Service seek method.'''

    async def execute(self, position):
        '''Seek the current song to the given position.'''
        self.data.seek(float(position))

class SetvolumeMethod(web.WebServiceMethod):
    '''Web Service setvolume method.'''

    async def execute(self, volume):
        '''Set the player's volume.'''
        self.data.setvolume(float(volume))

class SkipbackwardsMethod(web.WebServiceMethod):
    '''Web Service skipbackwards method.'''

    async def execute(self):
        '''Move the current position a bit backwards.'''
        self.data.skipbackwards()

class SkipforwardsMethod(web.WebServiceMethod):
    '''Web Service skipforwards method.'''

    async def execute(self):
        '''Move the current position a bit forwards.'''
        self.data.skipforwards()

class StatusMethod(web.WebServiceMethod):
    '''Web Service status method.'''

    async def execute(self):
        '''Return the status of the system.'''
        return self.data.status()

class StopMethod(web.WebServiceMethod):
    '''Web Service stop method.'''

    async def execute(self):
        '''Set the player to stop.'''
        self.data.stop()

############################### Core services #################################

class MusicServer:
    '''MusicServer interface.'''

    def __init__(self, configuration):
        # Create the player. This MusicServer is its listener
        self._player = Player(self)

        # Create the playlist
        self._create_playlist(configuration)

        # Start the player's event loop
        tornado.ioloop.IOLoop.current().spawn_callback(self._player.run)

    def _create_playlist(self, configuration):
        '''Create the playlist instance.'''
        # Get the directory where the songs will be stored
        try:
            songdir = configuration['musicserver']['songdir']
        except KeyError:
            songdir = DEFAULT_SONGDIR

        # Get the playlist size
        try:
            playlistsize = configuration['musicserver']['playlistsize']
        except KeyError:
            playlistsize = DEFAULT_PLAYLIST_SIZE

        # Create the playlist
        self._playlist = Playlist(songdir, playlistsize)

    def clear(self):
        '''Clear all songs in the playlist.'''
        # First, stop the player
        self._player.stop()

        # Then, clear the playlist
        self._playlist.clear()

    def close(self):
        '''Tell the music server that we're closing.'''
        self._player.close()

    def enqueue(self, title, data):
        '''Enqueue a song given its search id.'''
        self._playlist.enqueue(title, data)

    def next(self):
        '''Go to the next song in the playlist.'''
        # Stop the player, but first remember the current state
        player_state = self._player.state
        self._player.stop()

        # Go to the next song, but remember the index of the previous one
        self._playlist.next()

        # If the player was playing, set it to play
        if player_state == 'play':
            self._player.play(self._playlist.current)

    def pause(self):
        '''Set the player to play.'''
        self._player.pause()

    def play(self):
        '''Set the player to play.'''
        song = self._playlist.current
        if song:
            self._player.play(song)
        else:
            raise IndexError('no songs to play')

    def prev(self):
        '''Go to the previous song in the playlist.'''
        # Stop the player, but first remember the current state
        player_state = self._player.state
        self._player.stop()

        # Go to the previous song
        self._playlist.prev()

        # If the player was playing before, set it to play
        if player_state == 'play':
            self._player.play(self._playlist.current)

    def playereos(self):
        '''The EOS (End Of Stream) condition was received by the player.'''
        # When EOS, play the next song, if any
        try:
            self.next()
        except IndexError: pass

    def playererror(self, msg):
        '''An error was detected by the player.'''
        err, debuginfo = msg.parse_error()
        logging.error(
            f'error in pipeline: {msg.src.get_name()}: {err.message}')
        logging.error(f"debug info: {debuginfo if debuginfo else 'none'}")

    def remove(self, index):
        '''Remove the given song from the playlist.'''
        if index < 0:
            raise ValueError('index must be non-negative')
        # If the song removed is the current one, stop the player first.
        # Remember the original player state
        if index == self._playlist.currentindex:
            player_state = self._player.state
            self._player.stop()
            self._playlist.remove(index)
            song = self._playlist.current
            if player_state == 'play' and song:
                self._player.play(song)
        else:
            # if not, simply remove the song
            self._playlist.remove(index)

    def seek(self, position):
        '''Seek the current song to the given position.'''
        # Seek only if the player is not stopped
        self._player.seek(position)

    def setvolume(self, volume):
        '''Set the player's volume.'''
        self._player.setvolume(volume)

    def skipbackwards(self):
        '''Move the stream position a fixed amount backwards.'''
        self._player.skipbackwards()

    def skipforwards(self):
        '''Move the stream position a fixed amount forwards.'''
        self._player.skipforwards()

    def status(self):
        '''Return the status of the system.'''
        return {
            'playlist': self._playlist.status().serialize(),
            'player': self._player.status().serialize()
        }

    def stop(self):
        '''Set the player to stop.'''
        if self._player.state == 'stop':
            raise ValueError('already stopped')
        else:
            self._player.stop()

class Player:
    '''Plays songs.'''

    _STATES = {
        Gst.State.NULL: 'stop',
        Gst.State.READY: 'stop',
        Gst.State.PAUSED: 'pause',
        Gst.State.PLAYING: 'play'
    }

    def __init__(self, listener):
        self._state = 'stop'
        self._listener = listener
        self._closing = False
        self._song = None
        self._position = None

        # Initialize gstreamer
        Gst.init()

        # Build the gstreamer pipeline
        self._pipeline = Gst.parse_launch("playbin")

    def __del__(self):
        '''Set the pipeline to NULL to allow neat cleanup of resources.'''
        try:
            self._pipeline.set_state(Gst.State.NULL)
        except Exception: pass

    @property
    def state(self):
        '''Return the playing state of this player.'''
        return self._state

    def close(self):
        '''Close the player.'''
        self._closing = True

    def pause(self):
        '''Set the player to pause.'''
        if self._state == 'play':
            self._pipeline.set_state(Gst.State.PAUSED)
        else:
            raise ValueError('player not in PLAY state')

    def play(self, song):
        '''Set the player to play.'''
        # Set the song to play
        if self._song != song:
            self._song = song
            path = os.path.abspath(song.path)
            self._pipeline.set_property('uri', f'file://{path}')

        # Set the pipeline to PLAYING state
        self._pipeline.set_state(Gst.State.PLAYING)

    async def run(self):
        '''Run the main loop that plays the songs.'''
        bus = self._pipeline.get_bus()
        while not self._closing:
            msg = bus.pop_filtered(Gst.MessageType.ERROR | Gst.MessageType.EOS
                | Gst.MessageType.STATE_CHANGED | Gst.MessageType.SEGMENT_DONE)

            # Check the received message
            if msg:
                self._handle_message(msg)
            else:
                if self._state != 'stop':
                    # Update song attributes
                    self._update_song_attributes()
                else:
                    self._position = None

                # Wait for a given time
                await tornado.gen.sleep(DEFAULT_EVENT_WAIT_TIME)

        # Closing the player
        self._pipeline.set_state(Gst.State.NULL)

    def seek(self, position):
        '''Set the stream position.'''
        if not 0.0 <= position <= 1.0:
            raise ValueError('wrong position value')

        # Seek only if the player is not in stop state
        if self._state != 'stop' and self._song.duration is not None:
            position = self._song.duration * position
            self._pipeline.seek_simple(Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                int(position * Gst.SECOND))
        else:
            raise ValueError('player stopped')

    def setvolume(self, volume):
        '''Set the playing volume.'''
        if not 0.0 <= volume <= 1.0:
            raise ValueError('wrong volume')
        self._pipeline.set_property('volume', volume)

    def skipbackwards(self):
        '''Move the stream position a fixed amount backwards.'''
        if (self._state != 'stop' and self._song.duration is not None
                and self._position is not None):
            newpos = max(self._position - 10.0, 0.0)
            self._pipeline.seek_simple(Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                int(newpos * Gst.SECOND))
        else:
            raise ValueError('player stopped')

    def skipforwards(self):
        '''Move the stream position a fixed amount forwards.'''
        if (self._state != 'stop' and self._song.duration is not None
                and self._position is not None):
            newpos = min(self._position + 10.0, self._song.duration)
            self._pipeline.seek_simple(Gst.Format.TIME,
                Gst.SeekFlags.FLUSH | Gst.SeekFlags.KEY_UNIT,
                int(newpos * Gst.SECOND))
        else:
            raise ValueError('player stopped')

    def status(self):
        '''Return the status of the player.'''
        return PlayerStatus(
            self._state, self._position, self._pipeline.get_property('volume'))

    def stop(self):
        '''Stop playing the current song.'''
        self._pipeline.set_state(Gst.State.READY)

    def _handle_message(self, msg):
        '''Process the message received.'''
        if msg.type == Gst.MessageType.ERROR:
            # An error was received
            self._listener.playererror(msg)
        elif msg.type in [Gst.MessageType.EOS, Gst.MessageType.SEGMENT_DONE]:
            # The song has arrived to the end
            self._listener.playereos()
        elif msg.type == Gst.MessageType.STATE_CHANGED:
            if msg.src == self._pipeline:
                # The state has changed
                oldstate, newstate, pending = msg.parse_state_changed()
                self._state = self._STATES[newstate]
                if self._state == 'stop':
                    self._position = None

    def _update_song_attributes(self):
        '''Update the current song attributes, as duration and position.'''
        if self._song.duration is None:
            # Query the song's duration
            res, duration = self._pipeline.query_duration(Gst.Format.TIME)
            if res:
                self._song.setduration(duration / 1000000000)

        # Query the song's position
        res, position = self._pipeline.query_position(Gst.Format.TIME)
        if res:
            self._position = position / 1000000000

class PlayerStatus:
    '''Stores the status of the Player.'''

    def __init__(self, state, position, volume):
        self._state = state
        self._position = position
        self._volume = volume

    def serialize(self):
        '''Serialize this object.'''
        return {'state': self._state, 'position': self._position,
            'volume': self._volume}

class Playlist:
    '''Keeps a queue of songs to play.'''

    def __init__(self, songdir, size=10):
        self._queue = collections.deque()
        self._refcount = {}
        self._songdir = songdir
        self._size = size
        self._current = 0

        # Create the directory if it doesn't exist
        if not os.path.exists(self._songdir):
            os.mkdir(self._songdir)

        # Clear old songs
        self._clear_all_songs()

    def clear(self):
        '''Remove all songs in the playlist.'''
        self._queue.clear()
        self._refcount = {}
        self._clear_all_songs()
        self._current = 0

    @property
    def current(self):
        '''Return the current song in the playlist.'''
        if not self._queue:
            return None
        return self._queue[self._current]

    @property
    def currentindex(self):
        '''Return the index of the current song being played.'''
        if not self._queue:
            return None
        return self._current

    def enqueue(self, title, data):
        '''Enqueue a song in the playlist.'''
        # Compute the hash of the song
        hash_ = self._hash(data)

        # Save the song to disk if necessary
        try:
            self._refcount[hash_] += 1
        except KeyError:
            self._save(data, hash_)
            self._refcount[hash_] = 1

        # Instantiate a Song
        path = os.path.join(self._songdir, hash_)
        s = Song(title, path, hash_)

        # Add the song to the playlist
        self._queue.append(s)

        # Remove old songs from the playlist
        self._remove_songs()

    def next(self):
        '''Go to the next song.'''
        newindex = self._current + 1
        if newindex > len(self._queue) - 1:
            raise IndexError('no more songs')
        self._current = newindex

        # Remove old songs from the playlist
        self._remove_songs()

    def prev(self):
        '''Go to the previous song.'''
        newindex = self._current - 1
        if newindex < 0:
            raise IndexError('no more songs')
        self._current = newindex

    def remove(self, index):
        '''Remove the song with the given index from the playlist.'''
        # Check the index
        if index > len(self._queue) - 1:
            raise IndexError('no more songs')

        # Get the song to remove
        song = self._queue[index]

        # Update the refcount for this song
        self._remove_refcount(song)

        # Remove the song from the queue
        del self._queue[index]

        # Adjust the current index
        if index < self._current:
            self._current -= 1
        self._current = max(min(self._current, len(self._queue) - 1), 0)

    def status(self):
        '''Return the status of the playlist.'''
        return PlaylistStatus(self._queue, self.currentindex)

    def _clear_all_songs(self):
        '''Remove all the songs from the directory.'''
        for x in os.listdir(self._songdir):
            os.unlink(os.path.join(self._songdir, x))

    def _hash(self, data):
        '''Compute the hash of the given data.'''
        m = hashlib.sha256()
        m.update(data)
        return m.hexdigest()

    def _remove_songs(self):
        '''Remove old songs from the playlist to leave only one less that the
        maximum capacity.
        '''
        # Compute the number of elements to remove
        to_remove = min(self._current, max(0, len(self._queue) - self._size))

        # Remove songs
        for _ in range(to_remove):
            song = self._queue.popleft()

            # Reduce the counts for this song
            self._remove_refcount(song)

        # Update the current pointer
        self._current -= to_remove

    def _remove_refcount(self, song):
        '''Update the refcount of a given song as if it were going to be
        deleted. Delete the song file if the refcount gets to 0.
        '''
        # Reduce the counts for this song
        newrefcount = self._refcount[song.hash] - 1
        if newrefcount == 0:
            # The song is not used anymore, remove it from the directory
            os.unlink(song.path)
            del self._refcount[song.hash]
        else:
            # The song is still used, update the refcoung
            self._refcount[song.hash] = newrefcount

    def _save(self, data, name):
        '''Save the given song to the songs directory.'''
        with open(os.path.join(self._songdir, name), 'wb') as f:
            f.write(data)

class PlaylistStatus:
    '''Stores the status of the playlist.'''

    def __init__(self, songs, current):
        self._songs = songs
        self._current = current

    def serialize(self):
        '''Serialize this object.'''
        return {
            'songs': [s.todict() for s in self._songs],
            'current': self._current
        }

class Song:
    '''Represents a song.'''

    def __init__(self, title, path, hash_):
        self.title = title
        self.path = path
        self.hash = hash_
        self._duration = None

    @property
    def duration(self):
        '''Return the duration of this song.'''
        return self._duration

    def setduration(self, duration):
        '''Set the duration of this song.'''
        self._duration = duration

    def todict(self):
        '''Return a dictionary with the data of this song.'''
        return {'title': self.title, 'duration': self.duration}

