class Song:
    def __init__(self, url, name, ytId, thumbnail, duration, timestamp=None):
        self.url = url
        self.name = name
        self.ytId = ytId
        self.thumbnail = thumbnail
        self.timestamp = timestamp
        self.duration = duration
