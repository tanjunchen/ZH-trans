#!/usr/bin/env python

import pandas as pd
from os import stat
import os, requests
from jinja2 import Template
import pickle


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
    # 注意两次添加 否则出现问题
    dff = en_dff_files.append(zh_dff_files)
    dff = dff.drop_duplicates(subset=['file_path'], keep=False)
    files = dff['file_path'].to_list()
    return files


# 调用 github  https://api.github.com/graphql (v4) 获取数据
def get_data(query):
    r = requests.post("https://api.github.com/graphql", json={"query": query}, headers={
        "Authorization": "token %s" % "9669a965307bb1a37f1a0df336ec52073ea5eedd",
        "Accept": "application/vnd.github.ocelot-preview+json",
        "Accept-Encoding": "gzip"
    })
    r.raise_for_status()
    reply = r.json()
    return reply


def get_all_merged_pr(is_next=False, next_cursor=""):
    all_data = []
    if not is_next:
        # 首次使用
        first_query = """
                query {
                       repository(name: "istio-official-translation", owner: "servicemesher") {
                        issues(first: 100, labels: "version/1.4") {
                          pageInfo {
                            startCursor
                            endCursor
                            hasPreviousPage
                            hasNextPage
                          }
                          edges {
                            node {
                              title
                              url
                            }
                          }
                        }
                      }
                    }
                """
        result = get_data(first_query)
        next_cursor = result['data']['repository']['issues']['pageInfo']['endCursor']
        has_next_page = result['data']['repository']['issues']['pageInfo']['hasNextPage']
        prs = result['data']['repository']['issues']['edges']
        for pr in prs:
            title = pr["node"]["title"]
            url = str(pr["node"]["url"])
            all_data.append([title, url])
        if has_next_page:
            get_all_merged_pr(has_next_page, next_cursor)
    else:
        next_query = Template("""
                    query {
                        repository(name: "istio-official-translation", owner: "servicemesher") {
                            issues(
                            first: 100,
                            labels: "version/1.4",
                            after: "{{ next_cursor }}")
                            {
                                pageInfo{
                                    startCursor
                                    endCursor
                                    hasPreviousPage
                                    hasNextPage
                                }
                                edges {
                                node {
                                  title
                                  url
                                }
                            }
                            }
                        }
                    }
                    """).render({'next_cursor': next_cursor})
        result = get_data(next_query)
        next_cursor = result['data']['repository']['issues']['pageInfo']['endCursor']
        has_next_page = result['data']['repository']['issues']['pageInfo']['hasNextPage']
        next_prs = result['data']['repository']['issues']['edges']
        for pr in next_prs:
            title = pr["node"]["title"]
            url = str(pr["node"]["url"])
            all_data.append([title, url])
        if has_next_page:
            get_all_merged_pr(has_next_page, next_cursor)
    with open("issue.txt", 'wb') as f:
        pickle.dump(all_data, f)


if __name__ == '__main__':
    diff_file = diff_en_zh_files()
    # get_all_merged_pr()
    with open("issue.txt", 'rb') as f:
        content = pickle.load(f)
    issue_file = []
    for i in content:
        issue_file.append(i)
    ret_list = []
    for item in diff_file:
        if item not in issue_file:
            ret_list.append(item)

    for ii in ret_list:
        print(ii)