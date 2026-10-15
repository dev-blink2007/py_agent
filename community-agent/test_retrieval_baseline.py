from community_client import fetch_post_list

keywords = [
    "孙颖莎",
    "奥运会单打第二名",
    "东京奥运会",
]

for keyword in keywords:
    print("\n关键词：", keyword)
    print("结果：", fetch_post_list(keyword))