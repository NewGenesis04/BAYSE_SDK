from __future__ import annotations

from datetime import datetime

from pydantic import BaseModel, Field


class LoginResponse(BaseModel):
    token: str
    device_id: str = Field(alias="deviceId")
    user_id: str = Field(alias="userId")


class SigningInstructions(BaseModel):
    algorithm: str
    headers: list[str]
    payload_format: str = Field(alias="payloadFormat")
    timestamp_window_seconds: int = Field(alias="timestampWindowSeconds")


class ApiKey(BaseModel):
    id: str
    name: str
    public_key: str = Field(alias="publicKey")
    secret_key: str = Field(alias="secretKey")
    signing_instructions: SigningInstructions = Field(alias="signingInstructions")
    created_at: datetime = Field(alias="createdAt")


class ApiKeyListItem(BaseModel):
    id: str
    name: str
    public_key: str = Field(alias="publicKey")
    secret_key_hint: str = Field(alias="secretKeyHint")
    created_at: datetime = Field(alias="createdAt")


class ListApiKeysResponse(BaseModel):
    keys: list[ApiKeyListItem]
    total: int


class RevokeKeyResponse(BaseModel):
    message: str


class CreateApiKeyRequest(BaseModel):
    name: str


class UserProfile(BaseModel):
    id: str
    tag: str
    image_url: str = Field(alias="imageUrl")
