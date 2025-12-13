package com.example.ccbot_app.services;

import retrofit2.Retrofit;
import retrofit2.converter.gson.GsonConverterFactory;

public class RetrofitClient {

    private static final String URL_BASE = "https://1fe207621936.ngrok-free.app/    ";
    private static Retrofit retrofit = null;

    public static String getUrlBase() {
        return URL_BASE;
    }

    public static Retrofit getClient() {
        if (retrofit == null) {
            retrofit = new Retrofit.Builder()
                    .baseUrl(URL_BASE)
                    .addConverterFactory(GsonConverterFactory.create())
                    .build();
        }

        return retrofit;
    }
}
