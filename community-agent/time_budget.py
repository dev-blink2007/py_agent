class AgentDeadlineExceeded(Exception):
    """本次 Agent 运行的总时间预算已经耗尽。"""
    pass



def get_call_timeout(deadline, call_timeout, now):
    result = min(deadline-now,call_timeout)
    if result > 0:
        return result
    else :
        raise AgentDeadlineExceeded

if __name__ == "__main__":
    print(get_call_timeout(120,10,117))
    print(get_call_timeout(120,5,100))
    print(get_call_timeout(120,10,120))
    print(get_call_timeout(120,10,121))