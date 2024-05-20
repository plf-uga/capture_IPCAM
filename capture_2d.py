# -*- coding: utf-8 -*-
"""
Created on Wed Apr 6 16:13:01 2024

@author: Alves Lab 
"""

import os
import shutil
import math
from threading import Thread
import cv2
import time
from datetime import datetime
import configparser
os.chdir("C:\\Users\\alves\\OneDrive\\capture_IPCAM")

class VideoScreenshot(object):
    def __init__(self, src_list, camera_names, screenshot_interval, disk_limit):
        self.capture_list = []
        self.frame_list = []
        self.status_list = []
        self.screenshot_interval = screenshot_interval
        self.frame_width_list = []
        self.frame_height_list = []
        self.thread_list = []
        self.camera_names = camera_names
        self.disk_limit = disk_limit    
        

        for src in src_list:
            # Create a VideoCapture object for each source
            try:
                capture = cv2.VideoCapture(src)
                self.capture_list.append(capture)
                # Default resolutions of the frame are obtained (system dependent)
                frame_width = int(capture.get(3))
                frame_height = int(capture.get(4))
                self.frame_width_list.append(frame_width)
                self.frame_height_list.append(frame_height)

                # Initialize frame and status
                self.frame_list.append(None)
                self.status_list.append(False)

                # Start the thread to read frames from the video stream
                thread = Thread(target=self.update, args=(len(self.capture_list) - 1,))
                thread.daemon = True
                thread.start()
                self.thread_list.append(thread)
            except AttributeError:
                write_log("ERROR", f'Error when acessing {src}' , verbose = 1)
                

            

    def update(self, index):
        # Read the next frame from the stream in a different thread
        while True:
            if self.capture_list[index].isOpened():
                (self.status_list[index], self.frame_list[index]) = self.capture_list[index].read()

    def save_frame(self):
        last_save_time = time.time()
        
        total, used, free = shutil.disk_usage(os.getcwd())
        BytesPerGB = 1024**3
        free = float(free)/BytesPerGB        
    
        if (free - float(self.disk_limit)) > 20.0:
            while True:
                current_timestamp = time.time() - 2  
                # Convert the timestamp to the desired format
                current_time = time.strftime('%H%M%S', time.localtime(current_timestamp))
            
                for index in range(len(self.capture_list)):
                    if self.status_list[index]:
                        try:
                            output_folder = os.path.join(os.getcwd(), self.camera_names[index]+"_"+datetime.now().strftime('%Y_%m_%d'))
                            if not os.path.exists(output_folder):
                                os.makedirs(output_folder)                        
                            cv2.imwrite(os.path.join(output_folder, f'{self.camera_names[index]}_{current_time}.png'), self.frame_list[index])
                            write_log("INFO", f'Image {self.camera_names[index]}_{current_time}.png saved' , verbose = 1)
                        except AttributeError:
                            write_log("ERROR", f'Error when trying to save frame {self.camera_names[index]}_{current_time}.png' , verbose = 1)
                            pass       
            
                time.sleep(self.screenshot_interval)
        else:
            write_log("ERROR", f"Error, disk space reserved is less than 20GB!", verbose = 1)
            #print("Error, disk space reserved is less than 20GB!")

    def load_config(self):
        config = configparser.ConfigParser()
        config.read('config.ini')

        self.username = config.get('Camera', 'username')
        self.password = config.get('Camera', 'password')
        self.disk_limit = config.get('Disk', 'diskLimit')
        self.screenshot_interval = config.getint('Capture', 'interval_seconds')
        self.camera_names = [config.get('CamNames', key) for key in config['CamNames']]
        self.ips = [config.get('CameraIPs', key) for key in config['CameraIPs']] 
        
def write_log(info, message, verbose):
    current_timestamp = time.time()   
    # Convert the timestamp to the desired format
    current_time = time.strftime('%Y/%m/%d %H:%M:%S', time.localtime(current_timestamp))
    cout = f'{info} {current_time} : {message}  \n'
    with open('log.txt', 'a') as file:
        if verbose == 1:
            print(cout)
        file.write(cout)  
        

if __name__ == '__main__':   
            
    try:
            # Instantiate VideoScreenshot and load configuration
            video_stream_widget = VideoScreenshot([], [], [], [])
            video_stream_widget.load_config()
        
        
            # Create RTSP stream links using configuration
            rtsp_stream_links = []    
            for ip in video_stream_widget.ips:
                rtsp_stream_links.append(f'rtsp://{video_stream_widget.username}:{video_stream_widget.password}@{ip}/media/image1'.replace('#', '%23'))

            # Update VideoScreenshot with RTSP stream links
            video_stream_widget = VideoScreenshot(rtsp_stream_links, video_stream_widget.camera_names, video_stream_widget.screenshot_interval, video_stream_widget.disk_limit)
    
            # Start capturing frames and saving them
            video_stream_widget.save_frame()
    except KeyboardInterrupt:
            write_log("INFO","Process interrupted by user.", verbose = 1)
            #write_log("Process interrupted by user.")            
            # Release resources
            for capture in video_stream_widget.capture_list:
                capture.release()
            # Close all threads
            for thread in video_stream_widget.thread_list:
                thread.join()
    
        