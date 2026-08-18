import random

# 응답 코드 처리하는 함수
def http_status(method: str, success: float = 0.965, client_error: float = 0.027) -> int:

    r = random.random()
    # 정상
    if r < success:

        method = method.upper()
        if method == "GET":
            return 200
        if method == "POST":
            return random.choices([200, 201, 202, 204], weights=[48, 32, 15, 5], k=1)[0]
        if method in {"PUT", "PATCH"}:
            return random.choices([200, 204], weights=[80, 20], k=1)[0]
        if method == "DELETE":
            return random.choices([200, 204], weights=[25, 75], k=1)[0]
        return 200
    if r < success + client_error:
        # 클라이언트 오류
        return random.choices([400, 401, 403, 404, 409, 429], weights=[18, 14, 12, 24, 14, 18], k=1)[0]
    # 서버측 오류
    return random.choices([500, 502, 503, 504], weights=[45, 18, 27, 10], k=1)[0]