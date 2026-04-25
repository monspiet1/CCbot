package com.example.ccbot_app.services;

import com.example.ccbot_app.models.ChatRequest;
import com.example.ccbot_app.models.ChatResponse;

import retrofit2.Call;
import retrofit2.http.Body;
import retrofit2.http.POST;

public interface ApiService {
    // Define que faremos um POST na rota "/chat"
    // O corpo (@Body) será o ChatRequest
    // A resposta esperada é um ChatResponse
    @POST("chat")
    Call<ChatResponse> sendMessage(@Body ChatRequest request);
}
