import os
import numpy as np
import cv2
import time

import threading

import logging
from logging import getLogger
logger = getLogger(__name__)
logger.setLevel(logging.DEBUG)

#コンソール出力
sh = logging.StreamHandler()
logger.addHandler(sh)

IS_OPENCV3_LATER = True  # cv2.__version__.startswith("3.")

from collections import deque

#H264_flag = True
H264_flag = False

#一定時間の間隔に分割して動画を記録する
class VideoIntervalRecorder:

    def __init__(self,_record_dir,_base_file_name,video_fps,video_intarval_time=60*60*24):
        #logger.info("VideoIntervalRecorder init")
        self.record_dir = _record_dir
        #記録フォルダが存在しない場合作成
        if not os.path.isdir(self.record_dir):
            #logger.info("make movie dir = {}".format(self.record_dir))
            os.makedirs(self.record_dir)

        self.base_file_name = _base_file_name #datetime.now().strftime("%Y-%m-%d-%H-%M-%S")

        self.video_writer = cv2.VideoWriter();
        self.video_writer_enable = True
        self.video_part_no = 0
        self.video_begin_mmsec = 0
        self.VIDEO_FPS = video_fps
        self.VIDEO_TIME = int(video_intarval_time) #ビデオの長さ(sec)
        self.cur_video_path = ""

    #ビデオの解放
    def release(self):
        if self.video_writer is not None:
            if self.video_writer.isOpened():
                self.video_writer.release()
                self.video_writer = None
                logger.info(f"video release({self.cur_video_path})")

    #ビデオの記録
    def update(self,video_image,now_mmsec=0):
        if self.video_writer_enable is True:
            #初期化
            if self.video_writer.isOpened() is False:
                width  = video_image.shape[1]
                height = video_image.shape[0]
                #logger.info("bytes per pixel  = {}".format(video_image.shape[2]))
                #カラー？モノクロ)？
                is_color = 0 if video_image.shape[2] == 1 else 1

                #logger.info("video initialize ={},{},{}".format(width,height,self.VIDEO_FPS))
                #http://tessy.org/wiki/index.php?%A5%D3%A5%C7%A5%AA%A4%CE%BD%D0%CE%CF
                #動画のエンコード
                if IS_OPENCV3_LATER :
                    if H264_flag:
                        fourcc = cv2.VideoWriter_fourcc('H','2','6','4') # quick_time 拡張子は .m4v
                        ftype = ".mp4"#".avi"
                    else:
                        fourcc = cv2.VideoWriter_fourcc('m','p','4','v') # quick_time 拡張子は .m4v
                        ftype = ".m4v"
                        #fourcc = cv2.VideoWriter_fourcc('W', 'M', 'V', '2')# 拡張子は .wmv
                        #fourcc = cv2.VideoWriter_fourcc('M', 'P', '4', '3')# 拡張子は .mp4 Microsoft MPEG-4 Video Codec V3
                        #ftype = ".wmv"
                else:
                    if H264_flag:
                        fourcc = cv2.cv.CV_FOURCC('H','2','6','4') # quick_time 拡張子は .m4v
                        ftype = ".mp4"#".avi"
                    else:
                        fourcc = cv2.cv.CV_FOURCC('m','p','4','v') # quick_time 拡張子は .m4v
                        ftype = ".m4v"
                        #fourcc = cv2.cv.CV_FOURCC('W', 'M', 'V', '2')# 拡張子は .wmv
                        #fourcc = cv2.cv.CV_FOURCC('M', 'P', '4', '3')# 拡張子は .mp4 Microsoft MPEG-4 Video Codec V3
                        #ftype = ".wmv"

                #ビデオファイル名は、連番の名前で記録します。
                #http://qiita.com/haruakinosuke/items/518372ad304c1b71fa38
                #上記をみると FFMPEGというフリーソフトを使って、連番の動画ファイルを連結できます
                if self.VIDEO_TIME > 0:
                    number_padded = '%04d' % self.video_part_no
                    base_video_name = self.base_file_name + "-" + number_padded + ftype
                else:
                    base_video_name = self.base_file_name + ftype

                self.cur_video_path = os.path.join(self.record_dir,base_video_name)

                #ビデオを開始
                if self.video_writer.open(self.cur_video_path,fourcc,self.VIDEO_FPS,(width,height),isColor = is_color):
                    self.video_begin_mmsec = now_mmsec
                    self.video_writer.write(video_image) #最初のフレーム
                    #Logger.info("video file open ={}".format(self.cur_video_path))
                else:
                    logger.error("video writer init fault.disabled video wirte.")
                    self.video_writer_enable = False #video記録はできない
            #ビデオフレーム記録
            else:
                self.video_writer.write(video_image)
                elaped_time = ( now_mmsec - self.video_begin_mmsec ) / 1000.0
                ##logger.info("video time = {} , video_interval={}".format(elaped_time,self.VIDEO_TIME))
                if self.VIDEO_TIME != 0 and elaped_time > self.VIDEO_TIME:#指定時間がきたら一旦出力する。
                    #logger.info("release video = {}".format(self.cur_video_path))
                    self.video_writer.release()
                    #次のビデオ
                    self.video_part_no = self.video_part_no + 1
                    self.video_writer = cv2.VideoWriter()
                    #logger.info("video change no = {}".format(self.video_part_no))

#==========================================================
# exif_jpegを出力するスレッド
#==========================================================
class VideoIntervalRecorderThread(threading.Thread):
    def __init__(self, _record_dir,_base_file_name,_video_fps,_video_interval_time,rec_past_buffer_count=0):
        super(VideoIntervalRecorderThread, self).__init__()

        logger.info("VideoIntervalRecorderThread init")

        self.record_dir = _record_dir
        self.base_file_name = _base_file_name
        self.video_fps = _video_fps
        self.video_interval_time = _video_interval_time
        self.sec_per_frame = 1.0/(4.0 * _video_fps)
        self.queue_rgb_frame = []
        self.video_part_no = 0

        #過去記録
        #if rec_past_buffer_count > 10:
        #    self.rec_past_buffer = ImageBuffer(rec_past_buffer_count)
        #else:
        #    self.rec_past_buffer = None
        self.rec_past_buffer = None
        self.rec_past_output_path = None
        self.rec_past_output_fps = 10
        #一時記録
        self.rec_temp_video_recorder = None
        self.rec_temp_time = -1.0

        self.is_run = False

    #oooooooooooooooooooooooooooooooooooooooooooooooooooooooooo
    #追加機能1( 過去の動画を出力 ）・・・エラー時記録
    # 過去の指定フレーム数を出力をON
    def record_past_enable(self,rec_past_buffer_count=100):
        #最低 30フレーム
        self.rec_past_buffer = ImageBuffer(max(30,rec_past_buffer_count))

    def record_past_disable(self):
        self.rec_past_buffer = None #無効化

    def record_past_flush(self,file_path,fps):
        if self.rec_past_buffer is not None:
            if self.rec_past_output_path == None:
                self.rec_past_output_path = file_path
                self.rec_past_output_fps = fps
        else:
            logger.error("****** output_buffers not available! use set_output_buffers(). ******")

    #oooooooooooooooooooooooooooooooooooooooooooooooooooooooooo
    #追加機能2( 一時的な動画を出力 ）・・・運ぶ間中のみ記録
    # 一時記録開始
    def record_temp_start(self,temp_record_dir,temp_base_file_name,timeout_time = 6000):
        if self.rec_temp_video_recorder is not None:
            logger.info("already temp recording .this commannd is ignored. ")
            return
        self.rec_temp_video_recorder = VideoIntervalRecorder(temp_record_dir,temp_base_file_name,self.video_fps,0)
        self.rec_temp_time = timeout_time

    # 一時記録終了
    def record_temp_end(self):
        if self.rec_temp_video_recorder is not None:
            self.rec_temp_video_recorder.release()
            self.rec_temp_video_recorder = None
            self.rec_temp_time = -1.0
            return
        else:
            logger.info("temp recording is not running. ")
    #oooooooooooooooooooooooooooooooooooooooooooooooooooooooooo

    #デストラクタ
    def __del__(self):
        self.exit()

    def exit(self):
        logger.info("VideoIntervalRecorderThreadexit()")
        self.is_run = False

    def get_frame(self,rgb_frame):
        self.queue_rgb_frame.append( (rgb_frame) )

    def get_video_part_no(self):
        return self.video_part_no

    #スレッドの関数
    def run(self):
        self.is_run = True
        logger.info(" === start sub thread (sub class) === ")
        pre_time = time.clock()
        video_time_sec = 0.0
        video_recorder = VideoIntervalRecorder(self.record_dir,self.base_file_name,self.video_fps,self.video_interval_time)
        while self.is_run:
            #出力フレームがキューにあったら動画へ出力
            if len(self.queue_rgb_frame) > 0:
                now_time = time.clock()
                delta_time = now_time - pre_time
                pre_time = now_time
                video_time_sec += delta_time

                #最初の要素を削除して出力
                img = self.queue_rgb_frame.pop(0)
                #img=cv2.cvtColor(rgb_frame, cv2.COLOR_BGR2RGB)
                video_recorder.update(img,video_time_sec * 1000)
                self.video_part_no = video_recorder.video_part_no

                #一時記録
                if self.rec_temp_video_recorder is not None:
                    self.rec_temp_video_recorder.update(img,video_time_sec * 1000)
                    self.rec_temp_time -= delta_time
                    #タイムアウト
                    if self.rec_temp_time < 0.0:
                        logger.error("**** temp record is timeout **** ")
                        self.record_temp_end()

                #過去記録
                if self.rec_past_buffer is not None:
                    self.rec_past_buffer.append(img)
                    #出力命令があったら
                    if self.rec_past_output_path is not None:
                        buffer_path = self.rec_past_output_path
                        if self.rec_past_buffer.output_video(buffer_path,self.rec_past_output_fps):
                            self.rec_past_output_path = None
                 
            else:
                time.sleep( self.sec_per_frame )
        logger.info(" === end sub thread (sub class) === ")
        video_recorder.release()


#過去の指定フレームのバッファを保持し、コマンドがあったら動画出力する
class ImageBuffer():

    def __init__(self,buffer_length):
        self.buffer_length = buffer_length
        self.buffers = deque()

    def append(self,image):
        self.buffers.append(image)
        if len(self.buffers) > self.buffer_length:
            self.buffers.popleft()

    def output_video(self,file_path,fps):

        if len(self.buffers) > int(self.buffer_length*0.8):
            try:
                video_image = self.buffers[0]
                width  = video_image.shape[1]
                height = video_image.shape[0]
                logger.info("bytes per pixel  = {}".format(video_image.shape[2]))
                #カラー？モノクロ)？
                is_color = 0 if video_image.shape[2] == 1 else 1

                logger.info("video initialize ={},{},{}".format(width,height,fps))

                #http://tessy.org/wiki/index.php?%A5%D3%A5%C7%A5%AA%A4%CE%BD%D0%CE%CF
                #動画のエンコード
                if IS_OPENCV3_LATER :
                    if H264_flag:
                        fourcc = cv2.VideoWriter_fourcc('H','2','6','4') # quick_time 拡張子は .m4v
                        ftype = ".mp4"
                    else:
                        fourcc = cv2.VideoWriter_fourcc('m','p','4','v') # quick_time 拡張子は .m4v
                        ftype = ".m4v"
                        #fourcc = cv2.VideoWriter_fourcc('W', 'M', 'V', '2')# 拡張子は .wmv
                        #fourcc = cv2.VideoWriter_fourcc('M', 'P', '4', '3')# 拡張子は .mp4 Microsoft MPEG-4 Video Codec V3
                        #ftype = ".wmv"
                else:
                    if H264_flag:
                        fourcc = cv2.cv.CV_FOURCC('H','2','6','4') # quick_time 拡張子は .m4v
                        ftype = ".mp4"
                    else:
                        fourcc = cv2.cv.CV_FOURCC('m','p','4','v') # quick_time 拡張子は .m4v
                        ftype = ".m4v"
                        #fourcc = cv2.cv.CV_FOURCC('W', 'M', 'V', '2')# 拡張子は .wmv
                        #fourcc = cv2.cv.CV_FOURCC('M', 'P', '4', '3')# 拡張子は .mp4 Microsoft MPEG-4 Video Codec V3
                        #ftype = ".wmv"

                #親ディレクトリがなければ作る
                parent_dir = os.path.dirname(file_path)
                #フォルダが存在しない場合
                if not os.path.exists(parent_dir):
                    os.makedirs(parent_dir)

                #ビデオを開始
                video_writer = cv2.VideoWriter();
                if video_writer.open(file_path,fourcc,fps,(width,height),isColor = is_color):
                    logger.info("video file open ={}".format(file_path))
                    for img in self.buffers:
                        video_writer.write(img)
                    video_writer.release() #終了
                    logger.info("video file close={}".format(file_path))
                    video_writer = None
                    self.buffers.clear()
                video_writer = None
            except:
                logger.error("raise exception. ImageBuffer output_video")
            return True

        #logger.error("video writer init fault.disabled video wirte.({})".format(file_path))
        return False
