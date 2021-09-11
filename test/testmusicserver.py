
import json
import os
import shutil
import sys
import threading
import time
import unittest
import urllib.request


TEST_PATH = os.path.dirname(sys.argv[0])
ROOT_PATH = os.path.join(TEST_PATH, '..', 'src')

sys.path.insert(0, ROOT_PATH)
import musicserver

SLEEPTIME = 0.2

class MusicServerTestCase(unittest.TestCase):
    '''Test the music server.'''

    def _waitready(self):
        '''Wait until the server is ready.'''
        while not self._app.ready():
            time.sleep(0.1)

    def _status(self):
        '''Retrieve the status from the music server.'''
        url = 'http://localhost:8888/musicserver/status'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], False)
        return response['data']

    def setup(self):
        os.mkdir(os.path.join(TEST_PATH, 'songs'))

    def teardown(self):
        shutil.rmtree(os.path.join(TEST_PATH, 'songs'))

    def test_start_stop_server(self):
        '''Test start and stop the server.'''
        self._app = musicserver.Application(os.path.join(TEST_PATH, 'config1'))
        def f():
            self._waitready()
            self._app.stop()
        t = threading.Thread(target=f)
        t.start()        
        self._app.run()
        t.join()

    def test_clear_playlist(self):
        '''Test clear all the songs in the playlist.'''
        self._app = musicserver.Application(os.path.join(TEST_PATH, 'config2'))
        def f():
            self._waitready()
            self._clear()

            # Check the status
            self._check([], None, 'stop')

            # Enqueue a song
            song = os.path.join(TEST_PATH, 'song1.webm')
            self._enqueue(song, 'mysong')

            # Check the status
            self._check(['mysong'], 0, 'stop')

            # Clear the queue again
            self._clear()

            # Check the status
            self._check([], None, 'stop')
            self._app.stop()
        t = threading.Thread(target=f)
        t.start()        
        self._app.run()
        t.join()
        time.sleep(5)

    def _clear(self):
        '''Clear the playlist.'''
        url = 'http://localhost:8888/musicserver/clear'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], False)
        self.assertEquals(response['data'], None)

    def test_enqueue(self):
        '''Test enqueuing a song.'''
        self._app = musicserver.Application(os.path.join(TEST_PATH, 'config2'))
        def f():
            self._waitready()
            song = os.path.join(TEST_PATH, 'song1.webm')
            self._enqueue(song, 'mysong')

            # Check the status
            self._check(['mysong'], 0, 'stop')

            # Enqueue another song
            self._enqueue(song, 'mysong2')

            # Check the status
            self._check(['mysong', 'mysong2'], 0, 'stop')

            # Enqueue a third song
            self._next()
            self._enqueue(song, 'mysong3')

            # Check the status
            self._check(['mysong2', 'mysong3'], 0, 'stop')

            # Enqueue more songs
            song2 = os.path.join(TEST_PATH, 'song2.webm')
            self._next()            
            self._enqueue(song2, 'mysong4')
            self._check(['mysong3', 'mysong4'], 0, 'stop')
            self._next()
            self._enqueue(song2, 'mysong5')
            self._check(['mysong4', 'mysong5'], 0, 'stop')

            self._app.stop()
        t = threading.Thread(target=f)
        t.start()
        self._app.run()
        t.join()

    def _enqueue(self, song, title):
        '''Enqueue a song.'''
        headers = {
            'Content-Type': 'audio/mp4',
            'Content-Length': os.stat(song).st_size,
        }
        url = f'http://localhost:8888/musicserver/enqueue?title={title}'
        request = urllib.request.Request(
            url, open(song, 'rb'), headers=headers)
        with urllib.request.urlopen(request) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], False)
        self.assertEquals(response['data'], None)

    def _play(self, error=False, errmsg=None):
        '''Set the player to play.'''
        url = 'http://localhost:8888/musicserver/play'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def test_next(self):
        '''Test play the next song.'''
        self._app = musicserver.Application(os.path.join(TEST_PATH, 'config2'))
        def f():
            self._waitready()

            # Check the status
            self._check([], None, 'stop')

            # Try next when there's no songs in the playlist
            self._next(error=True, errmsg='no more songs')

            # Check the status
            self._check([], None, 'stop')

            # Try with some songs
            song = os.path.join(TEST_PATH, 'song1.webm')
            self._enqueue(song, 'mysong1')
            self._next(error=True, errmsg='no more songs')
            self._check(['mysong1'], 0, 'stop')
            self._enqueue(song, 'mysong2')
            self._next()
            self._check(['mysong1', 'mysong2'], 1, 'stop')
            self._next(error=True, errmsg='no more songs')
            self._check(['mysong1', 'mysong2'], 1, 'stop')
            self._enqueue(song, 'mysong3')
            self._check(['mysong2', 'mysong3'], 0, 'stop')
            self._enqueue(song, 'mysong4')
            self._check(['mysong2', 'mysong3', 'mysong4'], 0, 'stop')
            self._next()
            self._check(['mysong3', 'mysong4'], 0, 'stop')

            # Set the player to play
            self._play()
            time.sleep(SLEEPTIME)
            self._check(['mysong3', 'mysong4'], 0, 'play')
            self._next()
            time.sleep(SLEEPTIME)
            self._check(['mysong3', 'mysong4'], 1, 'play')
            self._next(error=True, errmsg='no more songs')
            time.sleep(SLEEPTIME)
            self._check(['mysong3', 'mysong4'], 1, 'stop')

            # Set the player to pause
            self._clear()
            self._enqueue(song, 'mysong1')
            self._enqueue(song, 'mysong2')
            self._check(['mysong1', 'mysong2'], 0, 'stop')
            self._play()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 0, 'play')
            self._pause()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 0, 'pause')
            self._next()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 1, 'stop')

            self._app.stop()         
        t = threading.Thread(target=f)
        t.start()
        self._app.run()
        t.join()

    def test_play_pause_stop(self):
        '''Test pause the current song.'''
        self._app = musicserver.Application(os.path.join(TEST_PATH, 'config2'))
        def f():
            self._waitready()

            # Check the status
            self._check([], None, 'stop')

            # Set the player to pause, without any song enqueued
            self._pause(error=True, errmsg='player not in PLAY state')
            self._check([], None, 'stop')

            # Set the player to play, without any song enqueued
            self._play(error=True, errmsg='no songs to play')
            self._check([], None, 'stop')

            # Enqueue a song and set it to pause
            song = os.path.join(TEST_PATH, 'song1.webm')
            self._enqueue(song, 'mysong1')
            self._pause(error=True, errmsg='player not in PLAY state')
            self._check(['mysong1'], 0, 'stop')
            self._play()
            time.sleep(SLEEPTIME)
            self._check(['mysong1'], 0, 'play')
            self._pause()
            time.sleep(SLEEPTIME)
            self._check(['mysong1'], 0, 'pause')
            self._play()
            time.sleep(SLEEPTIME)
            self._check(['mysong1'], 0, 'play')
            self._stop()
            time.sleep(SLEEPTIME)
            self._check(['mysong1'], 0, 'stop')

            # Re-stop
            self._stop(error=True, errmsg='already stopped')
            time.sleep(SLEEPTIME)
            self._check(['mysong1'], 0, 'stop')

            self._app.stop()         
        t = threading.Thread(target=f)
        t.start()
        self._app.run()
        t.join()

    def _next(self, error=False, errmsg=None):
        '''Go to the next song.'''
        url = 'http://localhost:8888/musicserver/next'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def _check(self, songs, current, state, position=-1, volume=None):
        '''Check the state of the server.'''
        status = self._status()
        l = [x['title'] for x in status['playlist']['songs']]
        self.assertEquals(l, songs)
        self.assertEquals(status['playlist']['current'], current)
        self.assertEquals(status['player']['state'], state)
        if position != -1:
            self.assertEquals(status['player']['position'], position)
        if volume is not None:
            self.assertEquals(status['player']['volume'], volume)
        return status

    def _pause(self, error=False, errmsg=None):
        '''Set the player to pause.'''
        url = 'http://localhost:8888/musicserver/pause'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def _stop(self, error=False, errmsg=None):
        '''Set the player to stop.'''
        url = 'http://localhost:8888/musicserver/stop'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def test_prev(self):
        '''Test play the previous song.'''
        self._app = musicserver.Application(os.path.join(TEST_PATH, 'config2'))
        def f():
            self._waitready()

            # Check the status
            self._check([], None, 'stop')

            # Try next when there's no songs in the playlist
            self._prev(error=True, errmsg='no more songs')

            # Check the status
            self._check([], None, 'stop')

            # Try with some songs
            song = os.path.join(TEST_PATH, 'song1.webm')
            self._enqueue(song, 'mysong1')
            self._prev(error=True, errmsg='no more songs')
            self._check(['mysong1'], 0, 'stop')
            self._enqueue(song, 'mysong2')
            self._next()
            self._check(['mysong1', 'mysong2'], 1, 'stop')
            self._prev()
            self._check(['mysong1', 'mysong2'], 0, 'stop')

            # Set the player to play
            self._play()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 0, 'play')
            self._next()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 1, 'play')
            self._prev()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 0, 'play')
            self._prev(error=True, errmsg='no more songs')
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 0, 'stop')

            # Set the player to pause
            self._next()
            self._play()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 1, 'play')
            self._pause()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 1, 'pause')
            self._prev()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 0, 'stop')

            self._app.stop()         
        t = threading.Thread(target=f)
        t.start()
        self._app.run()
        t.join()

    def _prev(self, error=False, errmsg=None):
        '''Go to the previous song.'''
        url = 'http://localhost:8888/musicserver/prev'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def test_remove(self):
        '''Test removing songs.'''
        self._app = musicserver.Application(os.path.join(TEST_PATH, 'config4'))
        def f():
            self._waitready()

            # Check the status
            self._check([], None, 'stop')

            # Try to remove when there's no songs in the playlist
            self._remove(0, error=True, errmsg='no more songs')
            self._check([], None, 'stop')
            self._remove(1, error=True, errmsg='no more songs')
            self._check([], None, 'stop')
            self._remove(-1, error=True, errmsg='index must be non-negative')
            self._check([], None, 'stop')

            # Remove the only song enqueued
            song = os.path.join(TEST_PATH, 'song1.webm')
            self._enqueue(song, 'mysong')
            self._check(['mysong'], 0, 'stop')
            self._remove(0)
            self._check([], None, 'stop')
            self._enqueue(song, 'mysong')
            self._play()
            time.sleep(SLEEPTIME)
            self._check(['mysong'], 0, 'play')
            self._remove(0)
            time.sleep(SLEEPTIME)
            self._check([], None, 'stop')            

            # Remove a song before the current one
            self._enqueue(song, 'mysong1')
            self._enqueue(song, 'mysong2')
            self._next()
            self._check(['mysong1', 'mysong2'], 1, 'stop')
            self._remove(0)
            self._check(['mysong2'], 0, 'stop')
            self._enqueue(song, 'mysong1')
            self._play()
            time.sleep(SLEEPTIME)
            self._next()
            time.sleep(SLEEPTIME)
            self._check(['mysong2', 'mysong1'], 1, 'play')
            self._remove(0)
            self._check(['mysong1'], 0, 'play')

            # Remove the current song
            self._stop()
            time.sleep(SLEEPTIME)
            self._enqueue(song, 'mysong2')
            self._enqueue(song, 'mysong3')
            self._next()
            self._check(['mysong1', 'mysong2', 'mysong3'], 1, 'stop')
            self._remove(1)
            self._check(['mysong1', 'mysong3'], 1, 'stop')
            self._remove(1)
            self._check(['mysong1'], 0, 'stop')
            self._enqueue(song, 'mysong2')
            self._enqueue(song, 'mysong3')
            self._play()
            time.sleep(SLEEPTIME)
            self._next()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2', 'mysong3'], 1, 'play')
            self._remove(1)
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong3'], 1, 'play')
            self._remove(1)
            time.sleep(SLEEPTIME)
            self._check(['mysong1'], 0, 'play')

            # Remove a song after the current one
            self._stop()
            time.sleep(SLEEPTIME)
            self._enqueue(song, 'mysong2')
            self._enqueue(song, 'mysong3')
            self._next()
            self._check(['mysong1', 'mysong2', 'mysong3'], 1, 'stop')
            self._remove(2)
            self._check(['mysong1', 'mysong2'], 1, 'stop')
            self._play()
            time.sleep(SLEEPTIME)
            self._enqueue(song, 'mysong3')
            self._check(['mysong1', 'mysong2', 'mysong3'], 1, 'play')
            self._remove(2)
            self._check(['mysong1', 'mysong2'], 1, 'play')

            self._app.stop()         
        t = threading.Thread(target=f)
        t.start()
        self._app.run()
        t.join()

    def _remove(self, index, error=False, errmsg=None):
        '''Go to the previous song.'''
        url = f'http://localhost:8888/musicserver/remove?index={index}'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def test_seek(self):
        '''Test seeking into a song.'''
        self._app = musicserver.Application(os.path.join(TEST_PATH, 'config4'))
        def f():
            self._waitready()

            # Check the status
            self._check([], None, 'stop')

            # Try to seek when there's no songs in the playlist
            self._seek(0, error=True, errmsg='player stopped')
            self._check([], None, 'stop', None)
            self._seek(0.5, error=True, errmsg='player stopped')
            self._check([], None, 'stop', None)
            self._seek(1.0, error=True, errmsg='player stopped')
            self._check([], None, 'stop', None)

            # Enqueue two songs and try seek
            song = os.path.join(TEST_PATH, 'song1.webm')
            self._enqueue(song, 'mysong1')
            self._enqueue(song, 'mysong2')
            self._play()
            time.sleep(SLEEPTIME)
            status = self._check(['mysong1', 'mysong2'], 0, 'play')
            duration = status['playlist']['songs'][0]['duration']
            self._seek(0.5)
            time.sleep(3.0)
            status = self._check(['mysong1', 'mysong2'], 0, 'play')
            self.assertTrue(status['player']['position'] > duration * 0.5)

            # Pause and seek
            self._pause()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 0, 'pause')
            self._seek(0.6)
            time.sleep(SLEEPTIME)
            status = self._check(['mysong1', 'mysong2'], 0, 'pause')
            self.assertTrue(
                abs(duration * 0.6 - status['player']['position']) < 5.0)

            # Play and seek to the end and wait for the other song to play
            self._play()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 0, 'play')
            self._seek(1.0)
            time.sleep(5.0)
            status = self._check(['mysong1', 'mysong2'], 1, 'play')
            self._seek(1.0)
            time.sleep(5.0)
            status = self._check(['mysong1', 'mysong2'], 1, 'stop')

            # Wrong seek
            self._play()
            time.sleep(SLEEPTIME)
            status = self._check(['mysong1', 'mysong2'], 1, 'play')
            self._seek(-0.1, error=True, errmsg='wrong position value')
            self._seek(1.1, error=True, errmsg='wrong position value')

            # Set the volume
            self._volume(-0.1, error=True, errmsg='wrong volume')
            self._volume(1.1, error=True, errmsg='wrong volume')
            self._volume(0.0)
            self._check(['mysong1', 'mysong2'], 1, 'play', volume=0.0)
            self._volume(0.5)
            self._check(['mysong1', 'mysong2'], 1, 'play', volume=0.5)
            self._volume(1.0)
            status = self._check(['mysong1', 'mysong2'], 1, 'play', volume=1.0)

            # Skip forwards
            self._stop()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 1, 'stop')
            self._skipforwards(error=True, errmsg='player stopped')
            time.sleep(SLEEPTIME)
            self._play()
            time.sleep(SLEEPTIME)
            status = self._check(['mysong1', 'mysong2'], 1, 'play')
            prevpos = status['player']['position']
            self._skipforwards()
            time.sleep(SLEEPTIME)
            status = self._check(['mysong1', 'mysong2'], 1, 'play')
            nextpos = status['player']['position']
            self.assertTrue(abs(nextpos - prevpos - 10.0) < 1.0)

            # Skip backwards
            self._stop()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2'], 1, 'stop')
            self._skipbackwards(error=True, errmsg='player stopped')
            self._play()
            time.sleep(SLEEPTIME)
            self._seek(0.5)
            time.sleep(SLEEPTIME)
            status = self._check(['mysong1', 'mysong2'], 1, 'play')
            prevpos = status['player']['position']
            self._skipbackwards()
            time.sleep(SLEEPTIME)
            status = self._check(['mysong1', 'mysong2'], 1, 'play')
            nextpos = status['player']['position']
            self.assertTrue(abs(prevpos - nextpos - 10.0) < 1.0)

            # Force an error
            song = os.path.join(TEST_PATH, 'config1')
            self._enqueue(song, 'config1')
            self._next()
            time.sleep(SLEEPTIME)
            self._check(['mysong1', 'mysong2', 'config1'], 2, 'stop')

            self._app.stop()         
        t = threading.Thread(target=f)
        t.start()
        self._app.run()
        t.join()

    def _seek(self, position, error=False, errmsg=None):
        '''Go to the previous song.'''
        url = f'http://localhost:8888/musicserver/seek?position={position}'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def _volume(self, volume, error=False, errmsg=None):
        '''Set the player's volume.'''
        url = f'http://localhost:8888/musicserver/setvolume?volume={volume}'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def _skipforwards(self, error=False, errmsg=None):
        '''Skip forwards.'''
        url = f'http://localhost:8888/musicserver/skipforwards'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

    def _skipbackwards(self, error=False, errmsg=None):
        '''Skip backwards.'''
        url = f'http://localhost:8888/musicserver/skipbackwards'
        with urllib.request.urlopen(url) as f:
            response = json.loads(f.read())
        self.assertEquals(response['error'], error)
        if errmsg:
            self.assertEquals(response['errmsg'], errmsg)
        if not response['error']:
            self.assertEquals(response['data'], None)

