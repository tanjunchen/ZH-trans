# 开发文档 
代码简单，下次整理优化，实现完全自动化。
## istio/istio.io 数据源
1.1 通过[GraphQL API v4](https://developer.github.com/v4/)拉取`istio/istio.io`已经`merged`的数据。
具体获取数据规则，可以参考相关文档。也可以选择[REST API v3](https://developer.github.com/v3/),参考资料丰富。
    
    ''' 
    query {
          repository(name: "istio.io", owner: "istio") {
                pullRequests(
                first:100,
                states:MERGED,
                labels:"translation/chinese") {
                    pageInfo{
                        startCursor
                        endCursor
                        hasPreviousPage
                        hasNextPage
                    }
                    edges {
                        node {
                          number
                          url
                        }
                    }
                }
            }
        }
    def get_data(query):
    query {
                  repository(name: "istio.io", owner: "istio") {
                    pullRequests(
                    first:100,
                    states:MERGED,
                    labels:"translation/chinese") {
                        pageInfo{
                            startCursor
                            endCursor
                            hasPreviousPage
                            hasNextPage
                        }
                        edges {
                            node {
                              number
                              url
                            }
                        }
                    }
                  }
                }
        r = requests.post("https://api.github.com/graphql",
                          json={"query": query},
                          headers={
                              "Authorization": "token %s" % token,
                              "Accept": "application/vnd.github.ocelot-preview+json",
                              "Accept-Encoding": "gzip"
                          })
        r.raise_for_status()
        reply = r.json()
        return reply
    '''


1.2 数据表，使用的是sqlite数据库。

    '''
     author表： CREATE TABLE author(
                            id INTEGER PRIMARY KEY AUTOINCREMENT,
                            github_id varchar(255), # github 账户
                            name varchar(255), # 名字
                            email varchar(255), # 邮箱
                            zh_trans_sum Integer(20), # 总翻译数
                            company varchar(255), # 公司
                            location varchar(255) # 地点
                        );
     docs表：CREATE TABLE docs (
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pr_number Int(20), # pr 对应的数字 唯一
                        pr_url varchar(300),  # pr url 
                        pr_author varchar(500), # 作者
                        pr_merged_time varchar(300), #  合并时间-格林尼治时间
                        pr_version varchar(255), # 版本号 
                        pr_files varchar(2000), # 提交的 pr 包含哪些文件
                        process smallint # 是否已经处理
                    );
     request_pull表：CREATE TABLE request_pull(
                        id INTEGER PRIMARY KEY AUTOINCREMENT,
                        pr_url varchar(300), # pr url
                        pr_number Int(20), # pr 对应的数字 唯一
                        process smallint # 是否处理
                    );
     zh_trans表：CREATE TABLE zh_trans(
                           id INTEGER PRIMARY KEY AUTOINCREMENT,
                           github_id varchar(255), # github 账户
                           pr_number Integer(32), # pr 对应的数字 唯一
                           zh_version varchar(255),# 版本号
                           merge_time varchar(255),#  合并时间-格林尼治时间
                           zh_sum Integer(32), # 中文数
                           flag smallint,  # 0 新增 1 更新
                           file_path varchar(1000) # 文件路径
                       );
     git_log_problems表：CREATE TABLE git_log_problems(
                        id INTEGER PRIMARY KEY AUTOINCREMENT, 
                        file_path varchar(1000),
                        zh_version varchar(255),
                        github_id varchar(255),
                        pr_number Integer(32),
                        merged_time varchar(255)
                    );
    '''

## Git 工具
1.1 python 调用[GitPython](https://github.com/gitpython-developers/GitPython)工具拉取远程仓库，在本地生成相应的分支。
基于`git`日志，基于正则匹配`result = re.findall(u"[\u4e00-\u9fa5]", content))`计算相应文件的中文字数。

## 数据展示
1.1 调用 pyecharts 展示相应的数据。[pyecharts 参考](https://github.com/pyecharts/pyecharts)

## 下一步计划
1.1 优化代码（封装、配置）、命令式自动化、dockerfile、flask web部署。

## 总结
其他中文翻译项目类似，github(git获取详细信息)、数据简单分析处理、数据展示。