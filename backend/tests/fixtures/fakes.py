"""External HTTP service fakes using respx."""

import json
import respx
import httpx


def fake_llm_server(router: respx.MockRouter, response_text: str | None = None, status_code: int = 200) -> respx.Route:
    """Mock Groq / OpenAI chat completion endpoint."""
    if response_text is None:
        response_text = json.dumps({
            "choices": [
                {
                    "message": {
                        "content": json.dumps([
                            {
                                "title": "SOC-2 Type II Compliance Deliverable",
                                "customer_name": "Acme Corp",
                                "promised_by": "2026-11-30",
                                "confidence": 0.95,
                                "category": "security",
                            }
                        ])
                    }
                }
            ]
        })
    else:
        response_text = json.dumps({
            "choices": [
                {
                    "message": {
                        "content": response_text
                    }
                }
            ]
        })

    return router.post("https://api.groq.com/openai/v1/chat/completions").mock(
        return_value=httpx.Response(status_code, text=response_text)
    )


def fake_stt_server(router: respx.MockRouter, transcript: str = "We commit to delivering the SOC2 report by Nov 30.", status_code: int = 200) -> respx.Route:
    """Mock Speech-To-Text transcription endpoint."""
    return router.post("https://api.groq.com/openai/v1/audio/transcriptions").mock(
        return_value=httpx.Response(status_code, json={"text": transcript})
    )


def fake_slack_server(router: respx.MockRouter, ok: bool = True, status_code: int = 200) -> list[respx.Route]:
    """Mock Slack auth and chat endpoints."""
    routes = []
    routes.append(
        router.post("https://slack.com/api/auth.test").mock(
            return_value=httpx.Response(status_code, json={"ok": ok, "user": "promisecheck_bot"})
        )
    )
    routes.append(
        router.post("https://slack.com/api/chat.postMessage").mock(
            return_value=httpx.Response(status_code, json={"ok": ok, "ts": "1728000000.000100"})
        )
    )
    routes.append(
        router.post(url__regex=r"^https://hooks\.slack\.com/.*").mock(
            return_value=httpx.Response(status_code, text="ok")
        )
    )
    return routes


def fake_jira_server(router: respx.MockRouter, ok: bool = True, status_code: int = 200) -> list[respx.Route]:
    """Mock Jira REST API endpoints."""
    routes = []
    routes.append(
        router.get(url__regex=r"^https://[^/]+/rest/api/3/myself").mock(
            return_value=httpx.Response(status_code, json={"accountId": "acc-123", "displayName": "Jira Test User"})
        )
    )
    routes.append(
        router.get(url__regex=r"^https://[^/]+/rest/api/3/issue/[^/]+").mock(
            return_value=httpx.Response(
                status_code,
                json={
                    "key": "ENG-101",
                    "fields": {
                        "summary": "Implement SSO Authentication",
                        "status": {"name": "In Progress"},
                        "duedate": "2026-11-30",
                    },
                },
            )
        )
    )
    return routes


def fake_linear_server(router: respx.MockRouter, status_code: int = 200) -> respx.Route:
    """Mock Linear GraphQL API endpoint."""
    return router.post("https://api.linear.app/graphql").mock(
        return_value=httpx.Response(
            status_code,
            json={
                "data": {
                    "viewer": {"id": "usr-linear-1", "name": "Linear Lead"},
                    "issue": {
                        "id": "iss-1",
                        "identifier": "LIN-42",
                        "title": "OAuth SSO Integration",
                        "state": {"name": "In Progress"},
                        "dueDate": "2026-11-30",
                    },
                }
            },
        )
    )


def fake_google_server(router: respx.MockRouter, status_code: int = 200) -> list[respx.Route]:
    """Mock Google OAuth token exchange and Google APIs."""
    routes = []
    routes.append(
        router.post("https://oauth2.googleapis.com/token").mock(
            return_value=httpx.Response(
                status_code,
                json={
                    "access_token": "ya29.mock_access_token",
                    "refresh_token": "1//mock_refresh_token",
                    "expires_in": 3600,
                    "token_type": "Bearer",
                },
            )
        )
    )
    routes.append(
        router.get(url__regex=r"^https://www\.googleapis\.com/calendar/.*").mock(
            return_value=httpx.Response(
                status_code,
                json={"status": "confirmed", "id": "ev-google-101", "summary": "Delivery Milestone"},
            )
        )
    )
    routes.append(
        router.post(url__regex=r"^https://gmail\.googleapis\.com/.*").mock(
            return_value=httpx.Response(status_code, json={"id": "msg-google-101", "labelIds": ["SENT"]})
        )
    )
    return routes
