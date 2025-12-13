package com.example.ccbot_app.adapters;

import android.content.Context;
import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.example.ccbot_app.R;
import com.example.ccbot_app.models.Message;

import java.util.List;

import io.noties.markwon.Markwon;

public class ChatAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {

    private final List<Message> messageList;
    private final Markwon markwon;

    public ChatAdapter(Context context, List<Message> messageList) {
        this.messageList = messageList;
        this.markwon = Markwon.create(context);
    }

    @Override
    public int getItemViewType(int position) {
        Message message = messageList.get(position);
        return message.getSender();
    }

    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        if (viewType == Message.SENT_BY_ME) {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_message_user, parent, false);
            return new UserViewHolder(view);
        } else {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_message_bot, parent, false);
            return new BotViewHolder(view);
        }
    }

    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
        Message message = messageList.get(position);

        TextView targetTextView;

        if (holder instanceof UserViewHolder) {
            targetTextView = ((UserViewHolder) holder).textMessage;
        } else {
            targetTextView = ((BotViewHolder) holder).textMessage;
        }

        markwon.setMarkdown(targetTextView, message.getText());
    }

    @Override
    public int getItemCount() {
        return messageList.size();
    }

    static class UserViewHolder extends RecyclerView.ViewHolder {
        TextView textMessage;
        UserViewHolder(@NonNull View itemView) {
            super(itemView);
            textMessage = itemView.findViewById(R.id.text_message_body);
        }
    }

    static class BotViewHolder extends RecyclerView.ViewHolder {
        TextView textMessage;
        BotViewHolder(@NonNull View itemView) {
            super(itemView);
            textMessage = itemView.findViewById(R.id.text_bot_response);
        }
    }
}
