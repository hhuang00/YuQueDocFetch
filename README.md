# YuQueDocFetch
![image](https://github.com/hhuang00/YuQueDocFetch/assets/108319401/141f087c-db64-4112-9141-6d1561f319c8)

本脚本使用python3编写
用于批量获取语雀下的个人知识库文档，并且按照原本的目录结构保存到本地，格式为docx。
## 使用方式
1. 首先导入所需要的库
`pip install -r requirements.txt`
2. 提供个人账号的x-csrf-token和Cookie并写到headers.txt中
3. 运行脚本
```
python YuQueDocFetch.py
或者
python YuQueDocFetch.py -p 指定下载路径
```

