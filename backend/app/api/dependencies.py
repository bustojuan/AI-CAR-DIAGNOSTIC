from fastapi import Request


def vehicles(request: Request):
    return request.app.state.vehicles


def conversations(request: Request):
    return request.app.state.conversations


def diagnostics(request: Request):
    return request.app.state.diagnostics
