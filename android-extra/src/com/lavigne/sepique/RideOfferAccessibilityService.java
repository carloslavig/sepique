package com.lavigne.sepique;

import android.accessibilityservice.AccessibilityService;
import android.accessibilityservice.AccessibilityServiceInfo;
import android.util.Log;
import android.view.accessibility.AccessibilityEvent;
import android.view.accessibility.AccessibilityNodeInfo;

import java.io.File;
import java.io.FileWriter;
import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/**
 * Le a tela de apps de corrida (Urbano Norte, inDriver, PopMove) quando um
 * pedido aparece, e grava os textos encontrados num arquivo JSON simples
 * dentro da pasta interna do app. O app Python (main.py / taximetro/offer.py)
 * le esse arquivo periodicamente e decide se a corrida compensa.
 *
 * So funciona se o usuario ativar manualmente em
 * Configuracoes > Acessibilidade > Se Pique (nao tem como ativar via codigo,
 * o Android exige esse passo manual por seguranca).
 */
public class RideOfferAccessibilityService extends AccessibilityService {
    private static final String TAG = "SePiqueOfferService";

    private static final List<String> TARGET_PACKAGES = Arrays.asList(
            "sinet.startup.inDriver",
            "br.com.urbanonorte.taxi.drivermachine",
            "br.com.popmove.driver"
    );

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
