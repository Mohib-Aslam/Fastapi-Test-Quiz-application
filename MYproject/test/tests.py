from fastapi.testclient import TestClient

import schemas
def test_register_success(client):
    r = client.post(
        "/register",
        json={"username": "alice", "email": "alice@example.com", "password": "password123"},
    )
    assert r.status_code == 200
    body = r.json()
    assert body["username"] == "alice"
    assert body["email"] == "alice@example.com"
    assert "id" in body
    assert "password" not in body
    assert "hashed_password" not in body
    
    
    #register tests

def test_register_duplicate_username_rejected(client):
    client.post("/register", json={"username": "alice", "email": "alice@example.com", "password": "pw123456"})
    r = client.post("/register", json={"username": "alice", "email": "someone-else@example.com", "password": "pw123456"})
    assert r.status_code == 400
    
def test_register_duplicate_email_rejected(client):
    client.post("/register", json={"username": "alice", "email": "alice@example.com", "password": "pw123456"})
    r = client.post("/register", json={"username": "someone-else", "email": "alice@example.com", "password": "pw123456"})
    assert r.status_code == 400 
    
def test_register_invalid_email_format_rejected(client):
    r = client.post("/register", json={"username": "alice", "email": "not-an-email", "password": "pw123456"})
    assert r.status_code == 422 
    
    
    
    # login tests
    
def test_login_success(client):
    client.post("/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"})
    r = client.post("/login", data={"username": "alice", "password": "password123"})
    assert r.status_code == 200
    body = r.json()
    assert "access_token" in body
    assert body["token_type"] == "bearer"
    
def test_login_invalid_password_rejected(client):
    client.post("/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"})
    r = client.post("/login", data={"username": "alice", "password": "wrongpassword"})
    assert r.status_code == 401
    
def test_login_invalid_username_rejected(client):
    client.post("/register", json={"username": "alice", "email": "alice@example.com", "password": "password123"})  
    r = client.post("/login", data={"username": "ghost", "password": "password123"})
    assert r.status_code == 401
    
    
    # Auth requirements tests
    
def test_create_quiz_requires_auth(client):
    r = client.post("/quizzes", json={"title": "T", "description": "D", "questions": []})
    assert r.status_code == 401
    
def test_get_quiz_requires_auth(client):
    r = client.get("/quizzes")
    assert r.status_code == 401
    
def test_endpoints_reject_invalid_token(client):
    r = client.get("/quizzes", headers={"Authorization": "Bearer invalidtoken"})
    assert r.status_code == 401
    
    
    #Quizzes create Tests
    

# dummy payload to use in tests
def _valid_quiz_payload():
    return {
        "title": "Capitals",
        "description": "Name that capital",
        "questions": [
            {
                "question_text": "Capital of France?",
                "options": ["Paris", "Lyon", "Nice"],
                "correct_option": "Paris",
            },
            {
                "question_text": "Capital of Japan?",
                "options": ["Osaka", "Tokyo"],
                "correct_option": "Tokyo",
            },
        ],
    }
    
def test_create_quiz_success(client, register_and_login):   
    headers = register_and_login()
    r = client.post("/quizzes", json=_valid_quiz_payload(), headers=headers)
    assert r.status_code == 201   
    body = r.json()
    assert body["title"] == "Capitals" 
    assert body["description"] == "Name that capital"
    assert body["short_code"]
    fetched = client.get(f"/quizzes/{body['id']}", headers=headers).json()
    assert len(fetched["questions"]) == 2
    
def test_create_quiz_without_questions_rejected(client, register_and_login):
    headers = register_and_login()
    payload = _valid_quiz_payload()
    payload["questions"] = []
    r = client.post("/quizzes", json=payload, headers=headers)
    assert r.status_code == 400

def test_create_quiz_with_single_option_rejected(client, register_and_login):
    headers = register_and_login()
    payload = _valid_quiz_payload()
    payload["questions"][0]["options"] = ["Only one option"]
    r = client.post("/quizzes", json=payload, headers=headers)
    assert r.status_code == 400
    
def test_create_quiz_with_correct_option_not_in_options_rejected(client, register_and_login):
    headers = register_and_login()
    payload = _valid_quiz_payload()
    payload["questions"][0]["correct_option"] = "Not in options"
    r = client.post("/quizzes", json=payload, headers=headers)
    assert r.status_code == 400

# Quizzes Get Tests

def test_get_quizzes_returns_only_user_quizzes(client, register_and_login):
    headers_alice = register_and_login("alice")
    headers_bob = register_and_login("bob")
    
    client.post("/quizzes", json=_valid_quiz_payload(), headers=headers_alice)
    client.post("/quizzes", json=_valid_quiz_payload(), headers=headers_bob)
    
    r = client.get("/quizzes", headers=headers_alice)
    assert r.status_code == 200
    assert len(r.json()) == 1

def test_get_quiz_by_id_success(client, register_and_login):
    headers = register_and_login()
    create_response = client.post("/quizzes", json=_valid_quiz_payload(), headers=headers)
    quiz_id = create_response.json()["id"]
    
    r = client.get(f"/quizzes/{quiz_id}", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert body["title"] == "Capitals"
    assert len(body["questions"]) == 2
    assert "correct_option" not in body["questions"][0]

def test_get_quiz_not_found(client, register_and_login):
    headers = register_and_login()
    r = client.get("/quizzes/9999", headers=headers)
    assert r.status_code == 404


# Quizzes Delete Tests

def test_delete_quiz_success(client, register_and_login):
    headers = register_and_login()
    create_response = client.post("/quizzes", json=_valid_quiz_payload(), headers=headers)
    quiz_id = create_response.json()["id"]
    
    r = client.delete(f"/quizzes/delete/{quiz_id}", headers=headers)
    assert r.status_code == 204
    
    # Verify it's deleted
    r_get = client.get(f"/quizzes/{quiz_id}", headers=headers)
    assert r_get.status_code == 404

def test_delete_quiz_not_found(client, register_and_login):
    headers = register_and_login()
    r = client.delete("/quizzes/delete/9999", headers=headers)
    assert r.status_code == 404
    
def test_delete_quiz_of_another_user_rejected(client, register_and_login):
    headers_alice = register_and_login("alice")
    headers_bob = register_and_login("bob")
    
    create_response = client.post("/quizzes", json=_valid_quiz_payload(), headers=headers_alice)
    quiz_id = create_response.json()["id"]
    
    r = client.delete(f"/quizzes/delete/{quiz_id}", headers=headers_bob)
    assert r.status_code == 404
    r = client.get(f"/quizzes/{quiz_id}", headers=headers_alice)
    assert r.status_code == 200
    
    
# Quizzes Public Access Tests

def test_get_quiz_by_short_code_success(client, register_and_login):
    headers = register_and_login()
    create_response = client.post("/quizzes", json=_valid_quiz_payload(), headers=headers)
    short_code = create_response.json()["short_code"]
    
    r = client.get(f"/quizzes/public/{short_code}")
    assert r.status_code == 200
    body = r.json()
    assert body["quiz"]["title"] == "Capitals"
    assert len(body["questions"]) == 2
    assert "correct_option" not in body["questions"][0]

def test_get_quiz_by_short_code_not_found(client):
    r = client.get("/quizzes/public/invalidcode")
    assert r.status_code == 404
    
def test_submit_quiz_scores_correctly(client, register_and_login):
    headers = register_and_login()
    create_response = client.post("/quizzes", json=_valid_quiz_payload(), headers=headers)
    short_code = create_response.json()["short_code"]
    
    public_data = client.get(f"/quizzes/public/{short_code}").json()
    q_ids = [q["id"] for q in public_data["questions"]]
    
    # Prepare answers
    answers = {
        "answers": {
            str(q_ids[0]): "Paris",  # Correct
            str(q_ids[1]): "Osaka"   # Incorrect
        }
    }
    
    r = client.post(f"/quizzes/public/{short_code}/submit", json=answers)
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 1
    assert body["total_questions"] == 2
    
def test_submit_quiz_with_all_correct_answers(client, register_and_login):
    headers = register_and_login()
    create_response = client.post("/quizzes", json=_valid_quiz_payload(), headers=headers)
    short_code = create_response.json()["short_code"]
    
    public_data = client.get(f"/quizzes/public/{short_code}").json()
    q_ids = [q["id"] for q in public_data["questions"]]
    
    # Prepare answers
    answers = {
        "answers": {
            str(q_ids[0]): "Paris",  # Correct
            str(q_ids[1]): "Tokyo"   # Correct
        }
    }
    
    r = client.post(f"/quizzes/public/{short_code}/submit", json=answers)
    assert r.status_code == 200
    body = r.json()
    assert body["score"] == 2
    assert body["total_questions"] == 2