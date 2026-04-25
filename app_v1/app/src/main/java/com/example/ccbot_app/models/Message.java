package com.example.ccbot_app.models;

public class Message {
    public static final int SENT_BY_ME = 0;
    public static final int SENT_BY_BOT = 1;
    public static final int SENT_BY_LOADING = 2;

    private String text;
    private int sender;

    public Message(String text, int sender) {
        this.text = text;
        this.sender = sender;
    }

    public String getText() {
        return text;
    }

    public int getSender() {
        return sender;
    }
}
