package com.example.ccbot_app.adapters;

import android.view.LayoutInflater;
import android.view.View;
import android.view.ViewGroup;
import android.widget.TextView;

import androidx.annotation.NonNull;
import androidx.recyclerview.widget.RecyclerView;

import com.example.ccbot_app.R;
import com.example.ccbot_app.models.Message;

import java.util.List;

public class ChatAdapter extends RecyclerView.Adapter<RecyclerView.ViewHolder> {

    private final List<Message> messageList;

    public ChatAdapter(List<Message> messageList) {
        this.messageList = messageList;
    }

    // Esse método diz pro Android qual tipo de visualização usar (Bot ou Usuário)
    @Override
    public int getItemViewType(int position) {
        Message message = messageList.get(position);
        return message.getSender(); // Retorna 0 ou 1
    }

    @NonNull
    @Override
    public RecyclerView.ViewHolder onCreateViewHolder(@NonNull ViewGroup parent, int viewType) {
        // Se for 0 (Usuário), carrega o layout da direita
        if (viewType == Message.SENT_BY_ME) {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_message_user, parent, false);
            return new UserViewHolder(view);
        }
        // Se for 1 (Bot), carrega o layout da esquerda
        else {
            View view = LayoutInflater.from(parent.getContext())
                    .inflate(R.layout.item_message_bot, parent, false);
            return new BotViewHolder(view);
        }
    }

    @Override
    public void onBindViewHolder(@NonNull RecyclerView.ViewHolder holder, int position) {
        Message message = messageList.get(position);

        // Preenche o texto dependendo de qual ViewHolder estamos usando
        if (holder instanceof UserViewHolder) {
            ((UserViewHolder) holder).textMessage.setText(message.getText());
        } else if (holder instanceof BotViewHolder) {
            ((BotViewHolder) holder).textMessage.setText(message.getText());
        }
    }

    @Override
    public int getItemCount() {
        return messageList.size();
    }

    // --- Classes internas para segurar os elementos da tela (ViewHolders) ---

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
