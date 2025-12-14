"""
data_prs.py
データの前処理を行う
"""


  #ライブラリのインポート
import re
import requests
import json
import os
import datetime
import pickle

#  データの前処理

  # 文字列が整数に変換可能かチェックし、可能なら整数に変換して返す
def str_to_int(txt:str)->int:
    if(re.match(r'^[0-9]+$',txt) is not None):
        return int(txt)
    else:
        print('this text includes some characters is not number')
        



  # パスワードがポリシーに適合するかチェック
def password_checker(password:str)->bool:
    if(len(password) <8 or len(password) >16):
        print("パスワードは8文字以上16文字以下で設定してください")
        return False
    if(re.search(r'[#,$,%,&]')!=None):
        print("パスワードに使用できない文字が含まれています")
        return False
    else:
        if(re.search(r'[a-zA-Z]',password)==None):
            pass
        if(re.search(r'[0-9]',password)==None):
            pass
        return True
    


#  jsonデータの取得、型変換→pickelで保存
def json_to_pickel(path:str):
    data = json.load(open(path,'r'))
    with open('data.pkl','wb') as f:
        pickle.dump(data,f) 



  # jsonデータの取得
def get_jsondata(url:str):
    response = requests.post(url, json={"key": "value"})
    if response.status_code == 200:
        json_data = response.json()
        print(json_data)
        return json_data
    #うまく取得ができなかったとき、ステータスコードを表示
    else:print(response.status_code)
    return None

  #  データの統計
class dataStat():
    def __init__(self):
        #当日の日付を取得
        self.current_time =datetime.datetime.now()
        #月毎(1~12)の廃棄量のリスト
        self.m_datas=[]
        #日毎(1~31)の廃棄量のリスト
        self.d_datas=[]
        #当日の廃棄量のリスト
        self.t_datas=[]

        
    def monthly_data(self):
        #合計を計算する
        self.m_datas[int(self.current_time.month)-1]=self.t_datas.sum()
        pass
    def daily_data(self):
        #合計を計算する
        self.d_datas[int(self.current_time.day)-1]=self.t_datas.sum()
        pass

 #廃棄データの統計をjsonファイルに保存
def  datastat_write(datastat:dataStat):
    data ={
        "monthly_data":datastat.m_datas,
        "daily_data":datastat.d_datas,
        
    }
    filename =f"data_stat.json"
    try:
        # 1. このスクリプトファイルの絶対パスを取得
        script_path = os.path.abspath(__file__)

        # 2. スクリプトファイルがあるディレクトリのパスを取得
        script_directory = os.path.dirname(script_path)

        # 3. 保存先ディレクトリ名を指定 (スクリプト基準の相対パス)
        save_directory_name = "../"

        # 4. スクリプトのディレクトリパスと保存先ディレクトリ名を結合
        save_directory_path = os.path.join(script_directory, save_directory_name)

        # 6. 最終的なファイルパスを結合
        file_path = os.path.join(save_directory_path, filename)
    except Exception as e:
        print("予期せぬエラーが発生しました: {e}")
    try:
        with open(file_path,'w') as file:
            json.dump(data,file,indent=4)
    except IOError as e:
        print(f"ファイルの書き込み中にエラーが発生しました: {e}")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}") 

  #データの読み込み※未完成
def read_json(path:str)->dict:
    try:
        with open(path,'r') as file:
            data = json.load(file)
            return data
    except FileNotFoundError:
        print("エラー: ファイルが見つかりません。")
    except Exception as e:
        print(f"予期せぬエラーが発生しました: {e}")

class dataLoad():
    def __init__(self,path:str):
        self.path = path

        pass
    def js_haiki(self):

        pass
    def js_user(self):
        
        pass





if __name__ == "__main__":
    pass