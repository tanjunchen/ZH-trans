#!/usr/bin/env python

import pandas as pd
import os
from os import stat


def get_files_path(file_path):
    content_list = []
    # 遍历文件夹
    """
    st_mode inode 保护模式
    st_ino  inode 节点号
    st_dev  inode 驻留的设备
    st_nlink=1  inode 的链接数
    st_uid=0    所有者的用户ID
    st_gid=0    所有者的组ID
    st_size=18330   普通文件以字节为单位的大小 包含等待某些特殊文件的数据。
    st_atime=1574756272 上次访问的时间
    st_mtime=1574756272 最后一次修改的时间
    st_ctime=1573697546 由操作系统报告的 ctime 在某些系统上 如 Unix 是最新的元数据更改的时间 
    在其它系统上 如 Windows 是创建时间 详细信息参见平台的文档 
    """
    for root, dirs, files in os.walk(file_path):
        for file in files:
            file_name = os.path.join(root, file)
            stat_info = stat(file_name)
            content_list.append([file_name, stat_info.st_mtime, stat_info.st_size])
    return content_list


def diff_en_zh_files():
    en_dff_files = pd.DataFrame(data=get_files_path("../istio.io/content/en/"),
                                columns=["file_path", "st_time", "st_size"])
    en_dff_files["file_path"] = en_dff_files["file_path"].apply(lambda x: x.replace("../istio.io/content/en/", ""))
    zh_dff_files = pd.DataFrame(data=get_files_path("../istio.io/content/zh/"),
                                columns=["file_path", "st_time", "st_size"])
    zh_dff_files["file_path"] = zh_dff_files["file_path"].apply(lambda x: x.replace("../istio.io/content/zh/", ""))

    dff = en_dff_files.append(zh_dff_files)
    # 注意两次添加，否则出现问题
    dff = en_dff_files.append(zh_dff_files)
    dff = dff.drop_duplicates(subset=['file_path'], keep=False)
    files = dff['file_path'].to_list()
    print(len(files))


if __name__ == '__main__':
    diff_en_zh_files()
