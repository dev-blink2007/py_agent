RETRIEVAL_CASES = [
    {
        "id": "connection_leak",
        "query": "请求处理完没有归还数据库连接，最后新请求拿不到连接，怎么修复？",
        "evidence_ids": [5],
    },
    {
        "id": "idle_connections",
        "query": "哪个参数控制连接池保留多少条闲置连接？",
        "evidence_ids": [6],
    },
    {
        "id": "sports_runner_up",
        "query": "哪位运动员在东京奥运会单打获得第二名？",
        "evidence_ids": [4],
    },
    {
        "id": "redis_refused",
        "query": "缓存连接被拒绝，最后是怎么恢复的？",
        "evidence_ids": [7],
    },
    {
        "id": "slow_query",
        "query": "帖子列表查询很慢，全表扫描的问题如何解决？",
        "evidence_ids": [8],
    },
    {
        "id": "expired_login",
        "query": "登录凭证过期导致接口返回401，应该怎么办？",
        "evidence_ids": [9],
    },
    {
        "id": "missing_score",
        "query": "孙颖莎东京奥运会女单决赛的具体比分是多少？",
        "evidence_ids": [],
    },
    {
        "id": "missing_configuration",
        "query": "本系统最大打开连接数具体配置成了多少？",
        "evidence_ids": [],
    },
]