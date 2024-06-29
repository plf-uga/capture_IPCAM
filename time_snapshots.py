# -*- coding: utf-8 -*-
"""
Created on Wed Apr 6 16:13:01 2024

@author: Alves Lab 
"""

import os
import shutil
import cv2
import time
from datetime import datetime
from threading import Thread
import configparser

os.chdir("/home/alveslab/RGB_Imgs")

class VideoScreenshot(object):
    def __init__(self, src_list, camera_names, screenshot_interval, disk_limit, duration):
        self.capture_list = []
        self.frame_list = []
        self.status_list = []
        self.screenshot_interval = screenshot_interval
        self.frame_width_list = []
        self.frame_height_list = []
        self.thread_list = []
        self.camera_names = camera_names
        self.disk_limit = disk_limit
        self.duration = duration * 60  # Convert minutes to seconds
        self.start_time = time.time()

        for src in src_list:
            try:
                capture = cv2.VideoCapture(src)
                self.capture_list.append(capture)
                frame_width = int(capture.get(3))
                frame_height = int(capture.get(4))
                self.frame_width_list.append(frame_width)
                self.frame_height_list.append(frame_height)

                self.frame_list.append(None)
                self.status_list.append(False)

                thread = Thread(target=self.update, args=(len(self.capture_list) - 1,))
                thread.daemon = True
                thread.start()
                self.thread_list.append(thread)
            except AttributeError:
                write_log("ERROR", f'Error when accessing {src}', verbose=1)

    def update(self, index):
        while True:
            try:
                if self.capture_list[index].isOpened():
                    (self.status_list[index], self.frame_list[index]) = self.capture_list[index].read()
                    if not self.status_list[index]:
                        write_log("ERROR", f"Frame read failed for camera {self.camera_names[index]}", verbose=1)
                        self.reconnect_camera(index)
                else:
                    write_log("ERROR", f"Camera {self.camera_names[index]} not opened", verbose=1)
                    self.reconnect_camera(index)
            except Exception as e:
                write_log("ERROR", f"Exception occurred for camera {self.camera_names[index]}: {e}", verbose=1)
                self.reconnect_camera(index)
            time.sleep(0.01)  # Adding a short sleep to reduce CPU usage
    
    def reconnect_camera(self, index):
        try:
            write_log("INFO", f"Attempting to reconnect to camera {self.camera_names[index]}", verbose=1)
            self.capture_list[index].release()
            time.sleep(2)  # Short delay before attempting to reconnect
            self.capture_list[index] = cv2.VideoCapture(self.capture_list[index].getBackendName())
            if self.capture_list[index].isOpened():
                write_log("INFO", f"Reconnected to camera {self.camera_names[index]}", verbose=1)
            else:
                write_log("ERROR", f"Failed to reopen camera {self.camera_names[index]}", verbose=1)
        except Exception as e:
            write_log("ERROR", f"Reconnection failed for camera {self.camera_names[index]}: {e}", verbose=1)

    def save_frame(self):
        total, used, free = shutil.disk_usage(os.getcwd())
        BytesPerGB = 1024**3
        free = float(free) / BytesPerGB

        if (free - float(self.disk_limit)) > 20.0:
            while True:
                if time.time() - self.start_time > self.duration:
                    write_log("INFO", "Snapshot duration completed.", verbose=1)
                    break

                current_timestamp = time.time() - 2
                current_time = time.strftime('%H%M%S', time.localtime(current_timestamp))

                for index in range(len(self.capture_list)):
                    if self.status_list[index]:
                        try:
                            output_folder = os.path.join(os.getcwd(), self.camera_names[index] + "_" + datetime.now().strftime('%Y_%m_%d'))
                            if not os.path.exists(output_folder):
                                os.makedirs(output_folder)
                            cv2.imwrite(os.path.join(output_folder, f'{self.camera_names[index]}_{current_time}.jpg'), self.frame_list[index])
                            write_log("INFO", f'Image {self.camera_names[index]}_{current_time}.jpg saved', verbose=1)
                        except AttributeError:
                            write_log("ERROR", f'Error when trying to save frame {self.camera_names[index]}_{current_time}.jpg', verbose=1)
                        except Exception as e:
                            write_log("ERROR", f'Exception occurred while saving frame {self.camera_names[index]}_{current_time}.jpg: {e}', verbose=1)
                    else:
                        write_log("WARNING", f"Camera {self.camera_names[index]} status is False", verbose=1)

                time.sleep(self.screenshot_interval)
        else:
            write_log("ERROR", "Error, disk space reserved is less than 20GB!", verbose=1)
    
    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')
        self.username = config.get('Camera', 'username')
        self.password = config.get('Camera', 'password')
        self.disk_limit = config.get('Disk', 'diskLimit')
        self.duration_minutes = config.getint('Time', 'duration')
        self.screenshot_interval = config.getint('Capture', 'interval_seconds')
        self.camera_names = [config.get('CamNames', key) for key in config['CamNames']]
        self.ips = [config.get('CameraIPs', key) for key in config['CameraIPs']]
    
def write_log(info, message, verbose):
    current_timestamp = time.time()
    current_time = time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(current_timestamp))
    cout = f'{info} {current_time} : {message}  \n'
    with open('log.txt', 'a') as file:
        if verbose == 1:
            print(cout)
        file.write(cout)

if __name__ == '__main__':
    try:
        video_stream_widget = VideoScreenshot([], [], [], [], 0)
        video_stream_widget.load_config()

        rtsp_stream_links = []
        for ip in video_stream_widget.ips:
            rtsp_stream_links.append(f'rtsp://{video_stream_widget.username}:{video_stream_widget.password}@{ip}/media/image1'.replace('#', '%23'))

        duration_minutes = video_stream_widget.duration_minutes

        video_stream_widget = VideoScreenshot(rtsp_stream_links, video_stream_widget.camera_names, video_stream_widget.screenshot_interval, video_stream_widget.disk_limit, duration_minutes)

        video_stream_widget.save_frame()
    except KeyboardInterrupt:
        write_log("INFO", "Process interrupted by user.", verbose=1)
        for capture in video_stream_widget.capture_list:
            capture.release()
        for thread in video_stream_widget.thread_list:
            thread.join()
