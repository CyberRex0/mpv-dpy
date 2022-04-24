# mpv-dpy
MPVとPulseAudioを使用し、高度な機能と可能性を備えた新しいDiscord音楽ボットの再生システム

# 動作要件
- Python 3.8以上
- [Discord.py](https://github.com/Rapptz/discord.py) v2.0
- PulseAudio
- MPV

# 使い方
## トークンの設定
config.pyを作成し、その中で`TOKEN`を定義してボットのトークンを入れてください。
```python
TOKEN='YourTokenHere'
```

## コマンド一覧
|コマンド名|説明|
|----------------|----------------|
|`t!vc con`|ボットをVCに参加させる|
|`t!vc dc`|ボットをVCから抜けさせる|
|`t!vc play ファイルパス(URL可)`|音楽ファイル/URLを再生する|
|`t!vc stop`|再生停止|
|`t!vc cmd COMMAND`|MPVに`COMMAND`というコマンドを送信する<br>**本番環境でこのコマンドを実装しないでください**|
|`t!vc seek RELATIVE_SEC`|`RELATIVE_SEC`秒だけシークする(負の値で巻き戻し)|
|`t!vc ui`|再生コントロール表示|

# Copyright
MIT License
&copy;2022 CyberRex