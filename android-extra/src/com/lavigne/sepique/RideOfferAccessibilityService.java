package com.lavigne.sepique;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.content.Context;
import android.content.Intent;
import android.graphics.Color;
import android.graphics.PixelFormat;
import android.os.Build;
import android.os.Handler;
import android.os.Looper;
import android.provider.Settings;
import android.util.Log;
import android.view.Gravity;
import android.view.View;
import android.view.WindowManager;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;
import android.widget.TextView;

import java.io.File;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Le a tela de apps de corrida (Urbano Norte, inDriver, PopMove) quando um
 * pedido aparece, grava os textos encontrados num arquivo JSON simples
 * dentro da pasta interna do app, e mostra uma bolha flutuante por cima do
 * outro app avisando que um pedido foi detectado. O app Python (main.py /
 * taximetro/offer.py) le esse arquivo periodicamente e decide se a corrida
 * compensa.
 *
 * Precisa de duas ativacoes manuais do usuario (o Android nao deixa nenhum
 * app ligar isso sozinho, por seguranca):
 *   1. Configuracoes > Acessibilidade > Se Pique
 *   2. Configuracoes > Apps > Se Pique > Exibir sobre outros apps
 * (a tela "Vale a corrida?" do app tem atalhos pras duas).
 */
public class RideOfferAccessibilityService extends AccessibilityService {
    private static final String TAG = "SePiqueOfferService";
    private static final long OVERLAY_COOLDOWN_MS = 8000;
    private static final long OVERLAY_AUTO_DISMISS_MS = 15000;

    private static final List<String> TARGET_PACKAGES = Arrays.asList(
            "sinet.startup.inDriver",
            "br.com.urbanonorte.taxi.drivermachine",
            "br.com.popmove.driver"
    );

    private WindowManager windowManager;
    private View overlayView;
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    private long lastOverlayAtMs = 0;

    @Override
    public void onAccessibilityEvent(AccessibilityEvent event) {
        CharSequence pkg = event.getPackageName();
        if (pkg == null || !TARGET_PACKAGES.contains(pkg.toString())) {
            return;
        }

        AccessibilityNodeInfo root = getRootInActiveWindow();
        if (root == null) {
            return;
        }

        List<String> texts = new ArrayList<>();
        collectText(root, texts);
        if (texts.isEmpty()) {
            return;
        }

        writeOffer(pkg.toString(), texts);
        showOverlay();
    }

    private void collectText(AccessibilityNodeInfo node, List<String> out) {
        if (node == null) {
            return;
        }
        CharSequence text = node.getText();
        if (text != null && text.length() > 0) {
            out.add(text.toString());
        }
        int childCount = node.getChildCount();
        for (int i = 0; i < childCount; i++) {
            AccessibilityNodeInfo child = node.getChild(i);
            if (child != null) {
                collectText(child, out);
                child.recycle();
            }
        }
    }

    private void writeOffer(String pkg, List<String> texts) {
        try {
            File outFile = new File(getFilesDir(), "last_offer.json");
            StringBuilder sb = new StringBuilder();
            sb.append("{\"package\":\"").append(escape(pkg)).append("\",");
            sb.append("\"detected_at_ms\":").append(System.currentTimeMillis()).append(",");
            sb.append("\"texts\":[");
            for (int i = 0; i < texts.size(); i++) {
                if (i > 0) {
                    sb.append(",");
                }
                sb.append("\"").append(escape(texts.get(i))).append("\"");
            }
            sb.append("]}");

            FileWriter writer = new FileWriter(outFile);
            writer.write(sb.toString());
            writer.close();
        } catch (Exception e) {
            Log.e(TAG, "Falha ao gravar last_offer.json", e);
        }
    }

    private String escape(String s) {
        return s.replace("\\", "\\\\").replace("\"", "'").replace("\n", " ");
    }

    private void showOverlay() {
        long now = System.currentTimeMillis();
        if (now - lastOverlayAtMs < OVERLAY_COOLDOWN_MS) {
            return;
        }
        if (!Settings.canDrawOverlays(this)) {
            return;
        }
        lastOverlayAtMs = now;
        mainHandler.post(this::addOverlayView);
    }

    private void addOverlayView() {
        if (windowManager == null) {
            windowManager = (WindowManager) getSystemService(Context.WINDOW_SERVICE);
        }
        removeOverlayView();

        TextView tv = new TextView(this);
        tv.setText("Se Pique: pedido detectado - toque pra ver se vale a pena");
        tv.setTextColor(Color.WHITE);
        tv.setBackgroundColor(Color.parseColor("#E01A2E22"));
        tv.setPadding(36, 26, 36, 26);
        tv.setTextSize(14);

        int overlayType = Build.VERSION.SDK_INT >= Build.VERSION_CODES.O
                ? WindowManager.LayoutParams.TYPE_APPLICATION_OVERLAY
                : WindowManager.LayoutParams.TYPE_PHONE;

        WindowManager.LayoutParams params = new WindowManager.LayoutParams(
                WindowManager.LayoutParams.WRAP_CONTENT,
                WindowManager.LayoutParams.WRAP_CONTENT,
                overlayType,
                WindowManager.LayoutParams.FLAG_NOT_FOCUSABLE
                        | WindowManager.LayoutParams.FLAG_NOT_TOUCH_MODAL,
                PixelFormat.TRANSLUCENT);
        params.gravity = Gravity.TOP | Gravity.CENTER_HORIZONTAL;
        params.y = 90;

        tv.setOnClickListener(v -> {
            openApp();
            removeOverlayView();
        });

        overlayView = tv;
        try {
            windowManager.addView(overlayView, params);
        } catch (Exception e) {
            Log.e(TAG, "Falha ao mostrar overlay", e);
            overlayView = null;
            return;
        }

        mainHandler.postDelayed(this::removeOverlayView, OVERLAY_AUTO_DISMISS_MS);
    }

    private void removeOverlayView() {
        if (overlayView != null && windowManager != null) {
            try {
                windowManager.removeView(overlayView);
            } catch (Exception ignored) {
            }
            overlayView = null;
        }
    }

    private void openApp() {
        try {
            Intent launch = getPackageManager().getLaunchIntentForPackage(getPackageName());
            if (launch != null) {
                launch.addFlags(Intent.FLAG_ACTIVITY_NEW_TASK);
                startActivity(launch);
            }
        } catch (Exception e) {
            Log.e(TAG, "Falha ao abrir o app", e);
        }
    }

    @Override
    public void onInterrupt() {
        // nada a fazer
    }

    @Override
    protected void onServiceConnected() {
        AccessibilityServiceInfo info = new AccessibilityServiceInfo();
        info.eventTypes = AccessibilityEvent.TYPE_WINDOW_STATE_CHANGED
                | AccessibilityEvent.TYPE_WINDOW_CONTENT_CHANGED;
        info.feedbackType = AccessibilityServiceInfo.FEEDBACK_GENERIC;
        info.flags = AccessibilityServiceInfo.FLAG_INCLUDE_NOT_IMPORTANT_VIEWS
                | AccessibilityServiceInfo.FLAG_REPORT_VIEW_IDS;
        info.notificationTimeout = 300;
        setServiceInfo(info);
    }
}
