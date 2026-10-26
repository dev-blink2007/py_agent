def read_detail_with_cache(post_id, cache, fetch_detail):
    if post_id in cache:
        return {"ok":True,"data":cache[post_id]},True
    else:
        result = fetch_detail(post_id)
        if result["ok"] == True:
            cache[post_id] = result["data"]
        return result,False