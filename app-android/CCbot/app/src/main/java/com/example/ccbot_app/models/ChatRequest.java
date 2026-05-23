package com.example.ccbot_app.models;

public class ChatRequest {
    private String pergunta;
    private String thread_id;

    public ChatRequest(String pergunta, String thread_id) {
        this.pergunta = pergunta;
        this.thread_id = thread_id;
    }

    public String getPergunta() { return pergunta; }
    public String getThread_id() { return thread_id; }
}
