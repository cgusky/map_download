# -*- coding: utf-8 -*-
#  coding=utf-8


import os, math, logging, requests, time

from map_download.cmd.BaseDownloader import DownloadEngine, BaseDownloaderThread, latlng2tile_terrain, BoundBox



def get_access_token(token):
    resp = None
    request_count = 0
    url = "https://api.cesium.com/v1/assets/1/endpoint"
    while True:
        if request_count > 4:
            break
        try:
            request_count += 1
            param = {'access_token': token}
            resp = requests.get(url, params=param, timeout=2)
            if resp.status_code != 200:
                continue
            break
        except Exception as e:
            resp = None
            time.sleep(3)
    if resp is None:
        return None
    resp_json = resp.json()
    return resp_json.get('accessToken')


class TerrainDownloaderThread(BaseDownloaderThread):
    URL = "https://assets.cesium.com/1/{z}/{x}/{y}.terrain?extensions=octvertexnormals-watermask&v=1.1.0"

    def __init__(self, root_dir, bbox, token, task_q, logger=None, write_db=False):
        super(TerrainDownloaderThread, self).__init__(root_dir, bbox, task_q, logger, write_db=write_db, db_file_name='Terrain.db')
        self.token = token

    def get_url(self, x, y, z):
        return self.URL.format(x=x, y=y, z=z)

    def _download(self, x, y, z):
        file_path = '%s/%s/%i/%i/%i.%s' % (self.root_dir, 'Terrain', z, x, y, 'terrain')
        if os.path.exists(file_path):
            self._data2DB(x, y, z, file_path)
            return 0
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        resp = None
        requre_count = 0
        _url = ''
        access_token = get_access_token(self.token)
        if access_token is None:
            return -1
        param = {'extensions': 'octvertexnormals-watermask', 'v': '1.1.0', 'access_token': access_token}
        while True:
            if requre_count > 4: break
            try:
                _url = self.get_url(x, y, z)
                resp = requests.get(_url, params=param, stream=True, timeout=2)
                break
            except Exception as e:
                resp = None
                time.sleep(3)
            requre_count += 1
        if resp is None:
            return -1
        if resp.status_code != 200:
            return -1
        try:
            with open(file_path, 'wb') as f:
                for chunk in resp.iter_content(chunk_size=1024):
                    if chunk:
                        f.write(chunk)
        except Exception as e:
            return -1
        self._data2DB(x, y, z, file_path)
        return 1


class TerrainDownloadEngine(DownloadEngine):
    root_dir = ''

    def __init__(self, root_dir, bbox, token, thread_num, logger=None, write_db=False):
        super(TerrainDownloadEngine, self).__init__(bbox, thread_num, logger, write_db=write_db)
        self.root_dir = root_dir
        self.token = token

    def bbox2xyz(self, z):
        min_x, min_y = latlng2tile_terrain(self.bbox.min_lat, self.bbox.min_lng, z)
        max_x, max_y = latlng2tile_terrain(self.bbox.max_lat, self.bbox.max_lng, z)
        return math.floor(min_x), math.floor(min_y), math.ceil(max_x) + 1, math.ceil(max_y) + 1

    def run(self):
        try:
            task_q = self.get_task_queue()
            self.threads = []
            self.division_done_signal.emit(task_q.qsize())
            for i in range(self.thread_num):
                thread = TerrainDownloaderThread(self.root_dir, self.bbox, self.token, task_q, self.logger, write_db=self.write_db)
                thread.sub_progressBar_updated_signal.connect(self.sub_update_progressBar)
                self.threads.append(thread)
            for thread in self.threads:
                thread.start()
            for thread in self.threads:
                thread.wait()
            self.download_done_signal.emit()
        except Exception as e:
            if self.logger is not None:
                self.logger.error(e)


if __name__ == '__main__':
    if 1:
        logger = logging.getLogger('down')
        try:
            root = r'/Users/cugxy/Documents/data/downloader'
            formatter = logging.Formatter('%(levelname)s-%(message)s')
            hdlr = logging.StreamHandler()
            log_file = os.path.join(root, 'down.log')
            file_hdlr = logging.FileHandler(log_file)
            file_hdlr.setFormatter(formatter)
            logger.addHandler(file_hdlr)
            logger.addHandler(hdlr)
            logger.setLevel(logging.INFO)
            min_lng = -180.0
            max_lng = 180.0
            min_lat = -90.0
            max_lat = 90.0
            start_zoom = 0
            end_zoom = 5
            bbox = BoundBox(max_lat, max_lng, min_lat, min_lng, start_zoom, end_zoom)
            d = TerrainDownloadEngine(root, bbox, 8, logger)
            d.start()
            time.sleep(10000)
            logger.error('main thread out')
        except Exception as e:
            logger.error(e)
    if 0:
        accessToken = get_access_token()
    pass

