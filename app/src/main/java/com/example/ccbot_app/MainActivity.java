package com.example.ccbot_app;

import android.os.Bundle;
import android.view.View;
import android.widget.EditText;
import android.widget.ImageButton;
import android.widget.TextView;

import androidx.activity.EdgeToEdge;
import androidx.appcompat.app.AppCompatActivity;
import androidx.core.graphics.Insets;
import androidx.core.view.ViewCompat;
import androidx.core.view.WindowInsetsCompat;
import androidx.recyclerview.widget.LinearLayoutManager;
import androidx.recyclerview.widget.RecyclerView;

import com.example.ccbot_app.adapters.ChatAdapter;
import com.example.ccbot_app.models.ChatRequest;
import com.example.ccbot_app.models.ChatResponse;
import com.example.ccbot_app.models.Message;
import com.example.ccbot_app.services.ApiService;
import com.example.ccbot_app.services.RetrofitClient;

import java.util.ArrayList;
import java.util.List;

import retrofit2.Call;
import retrofit2.Callback;
import retrofit2.Response;
import retrofit2.Retrofit;

public class MainActivity extends AppCompatActivity {

    RecyclerView recyclerView;
    EditText editTextInput;
    ImageButton buttonSend;

    List<Message> messageList;
    ChatAdapter chatAdapter;

    ApiService apiService;
    View layoutWelcome;
    TextView textWelcomeMessage;

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        EdgeToEdge.enable(this);
        setContentView(R.layout.activity_main);
        ViewCompat.setOnApplyWindowInsetsListener(findViewById(R.id.main), (v, insets) -> {
            Insets systemBars = insets.getInsets(WindowInsetsCompat.Type.systemBars());
            v.setPadding(systemBars.left, systemBars.top, systemBars.right, systemBars.bottom);
            return insets;
        });

        // 1. Inicializar as Views
        recyclerView = findViewById(R.id.recycler_chat);
        editTextInput = findViewById(R.id.edit_text_input);
        buttonSend = findViewById(R.id.button_send);
        layoutWelcome = findViewById(R.id.layout_welcome);

        textWelcomeMessage = findViewById(R.id.text_welcome_msg);

        // Texto que você quer animar
        String mensagem = "O que aprenderemos hoje?";

        // Chama a animação
        animateTextTyping(textWelcomeMessage, mensagem);

        // 2. Configurar a Lista e o Adapter
        messageList = new ArrayList<>();
        chatAdapter = new ChatAdapter(this, messageList);

        recyclerView.setAdapter(chatAdapter);
        LinearLayoutManager layoutManager = new LinearLayoutManager(this);
        layoutManager.setStackFromEnd(true); // Começa a lista de baixo para cima
        recyclerView.setLayoutManager(layoutManager);

        recyclerView.addOnLayoutChangeListener(new View.OnLayoutChangeListener() {
            @Override
            public void onLayoutChange(View v, int left, int top, int right, int bottom,
                                       int oldLeft, int oldTop, int oldRight, int oldBottom) {

                // Se a parte de baixo da lista subiu (bottom < oldBottom),
                // significa que o teclado apareceu (ou a tela diminuiu).
                if (bottom < oldBottom) {
                    // Rola suavemente para a última mensagem
                    if (messageList.size() > 0) {
                        recyclerView.postDelayed(new Runnable() {
                            @Override
                            public void run() {
                                recyclerView.smoothScrollToPosition(messageList.size() - 1);
                            }
                        }, 100); // Pequeno atraso para garantir que a animação do teclado terminou
                    }
                }
            }
        });

        Retrofit retrofit = RetrofitClient.getClient();
        apiService = retrofit.create(ApiService.class);

        // --- Ação do Botão ---
        buttonSend.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                String question = editTextInput.getText().toString().trim();

                if (!question.isEmpty()) {
                    sendMessageToApi(question);
                }
            }
        });
    }

    private void sendMessageToApi(String text) {

        messageList.add(new Message(text, Message.SENT_BY_ME));
        chatAdapter.notifyItemInserted(messageList.size() - 1);

        // Limpa input e esconde welcome
        editTextInput.setText("");

        if (layoutWelcome.getVisibility() == View.VISIBLE) {
            layoutWelcome.setVisibility(View.GONE);
        }

        // Adiciona a mensagem do Usuário na tela imediatamente
        messageList.add(new Message("...", Message.SENT_BY_LOADING));
        chatAdapter.notifyItemInserted(messageList.size() - 1);
        recyclerView.smoothScrollToPosition(messageList.size() - 1);

        // Prepara a requisição JSON: {"pergunta": "..."}
        ChatRequest request = new ChatRequest(text);

        // Faz a chamada para a API em segundo plano
        Call<ChatResponse> call = apiService.sendMessage(request);

        call.enqueue(new Callback<ChatResponse>() {
            @Override
            public void onResponse(Call<ChatResponse> call, Response<ChatResponse> response) {

                removeLoading();

                // Esse método roda quando o servidor responde
                if (response.isSuccessful() && response.body() != null) {
                    // Pega o texto da resposta: "Um array dinâmico é..."
                    String botReply = response.body().getResposta();
                    addBotMessage(botReply);
                } else {
                    addBotMessage("Erro: O servidor respondeu, mas houve um problema. Código: " + response.code());
                }
            }

            @Override
            public void onFailure(Call<ChatResponse> call, Throwable t) {
                removeLoading();
                // Esse método roda se não tiver internet ou o servidor estiver fora
                addBotMessage("Falha na conexão: " + t.getMessage());
            }
        });
    }

    // Método auxiliar para adicionar a resposta do bot na lista
    private void addBotMessage(String text) {
        messageList.add(new Message(text, Message.SENT_BY_BOT));
        chatAdapter.notifyItemInserted(messageList.size() - 1);
        recyclerView.smoothScrollToPosition(messageList.size() - 1);
    }

    // Método Mágico da Digitação
    private void animateTextTyping(final TextView textView, final String textToType) {
        final long delay = 50; // Velocidade da digitação (ms)
        final android.os.Handler handler = new android.os.Handler();

        // Limpa o texto inicial
        textView.setText("");

        // Cria a tarefa de rodar caractere por caractere
        Runnable characterAdder = new Runnable() {
            int index = 0;

            @Override
            public void run() {
                // Define o texto com um caractere a mais
                textView.setText(textToType.subSequence(0, index++));

                // Se ainda não acabou, agenda a próxima letra
                if (index <= textToType.length()) {
                    handler.postDelayed(this, delay);
                }
            }
        };

        // Inicia o processo
        handler.post(characterAdder);
    }

    // Método auxiliar para remover o último item se for LOADING
    private void removeLoading() {
        int lastPosition = messageList.size() - 1;
        if (lastPosition >= 0 && messageList.get(lastPosition).getSender() == Message.SENT_BY_LOADING) {
            messageList.remove(lastPosition);
            chatAdapter.notifyItemRemoved(lastPosition);
        }
    }
}