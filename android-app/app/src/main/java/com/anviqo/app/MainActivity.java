package com.anviqo.app;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.view.Gravity;
import android.view.View;
import android.view.ViewGroup;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;

public class MainActivity extends Activity {
    private static final int BG = Color.rgb(5, 11, 19);
    private static final int PANEL = Color.rgb(10, 20, 34);
    private static final int PANEL2 = Color.rgb(7, 16, 28);
    private static final int TEXT = Color.rgb(239, 246, 252);
    private static final int MUTED = Color.rgb(142, 163, 184);
    private static final int CYAN = Color.rgb(54, 215, 232);
    private static final int GREEN = Color.rgb(73, 230, 161);

    private LinearLayout root;
    private LinearLayout content;
    private WebView webView;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        showHome();
    }

    private TextView label(String text, float size, int color) {
        TextView v = new TextView(this);
        v.setText(text);
        v.setTextSize(size);
        v.setTextColor(color);
        v.setPadding(0, 4, 0, 4);
        return v;
    }

    private TextView title(String text) {
        TextView v = label(text, 22, TEXT);
        v.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        return v;
    }

    private TextView card(String name, String detail, String state) {
        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(20, 16, 20, 16);
        box.setBackgroundColor(PANEL);
        TextView n = label(name, 16, TEXT);
        n.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        box.addView(n);
        box.addView(label(detail, 12, MUTED));
        box.addView(label(state, 11, CYAN));
        LinearLayout.LayoutParams p = new LinearLayout.LayoutParams(-1, -2);
        p.setMargins(0, 0, 0, 12);
        content.addView(box, p);
        return n;
    }

    private Button navButton(String text, final View.OnClickListener click) {
        Button b = new Button(this);
        b.setText(text);
        b.setTextSize(10);
        b.setTextColor(TEXT);
        b.setAllCaps(false);
        b.setOnClickListener(click);
        return b;
    }

    private void base(String heading) {
        root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(BG);

        LinearLayout header = new LinearLayout(this);
        header.setGravity(Gravity.CENTER_VERTICAL);
        header.setPadding(18, 14, 18, 12);
        header.setBackgroundColor(PANEL);
        TextView logo = label("A", 24, CYAN);
        logo.setGravity(Gravity.CENTER);
        logo.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        header.addView(logo, new LinearLayout.LayoutParams(42, 42));
        LinearLayout htxt = new LinearLayout(this);
        htxt.setOrientation(LinearLayout.VERTICAL);
        htxt.setPadding(12, 0, 0, 0);
        htxt.addView(label("ANVIQO", 20, TEXT));
        htxt.addView(label("THINK • PREDICT • PROTECT", 9, MUTED));
        header.addView(htxt, new LinearLayout.LayoutParams(0, -2, 1));
        TextView online = label("● ONLINE", 11, GREEN);
        online.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        header.addView(online);
        root.addView(header);

        content = new LinearLayout(this);
        content.setOrientation(LinearLayout.VERTICAL);
        content.setPadding(18, 18, 18, 18);

        ScrollView scroll = new ScrollView(this);
        scroll.addView(content);
        root.addView(scroll, new LinearLayout.LayoutParams(-1, 0, 1));

        LinearLayout nav = new LinearLayout(this);
        nav.setBackgroundColor(PANEL2);
        nav.setGravity(Gravity.CENTER);
        nav.addView(navButton("Home", v -> showHome()), new LinearLayout.LayoutParams(0, 58, 1));
        nav.addView(navButton("ANVI", v -> openLive("Ask ANVI")), new LinearLayout.LayoutParams(0, 58, 1));
        nav.addView(navButton("Plant", v -> openLive("Plant Intelligence")), new LinearLayout.LayoutParams(0, 58, 1));
        nav.addView(navButton("Ops", v -> openLive("Operations")), new LinearLayout.LayoutParams(0, 58, 1));
        root.addView(nav);

        TextView safety = label("EVIDENCE FIRST  •  HUMAN GOVERNED  •  READ ONLY", 9, MUTED);
        safety.setGravity(Gravity.CENTER);
        safety.setPadding(0, 5, 0, 5);
        root.addView(safety);
        setContentView(root);
    }

    private void showHome() {
        base("Command Centre");
        content.addView(title("Command Centre"));
        content.addView(label("Industrial intelligence at a glance", 13, MUTED));
        content.addView(label("ANVIQO observes plant evidence, understands context, detects change and assists human decisions.", 13, TEXT));

        card("OBSERVE", "Live plant context • instruments • alarms • events", "LIVE MONITORING");
        card("UNDERSTAND", "Equipment identity • process context • evidence", "CONTEXT READY");
        card("PREDICT", "Early signals • abnormal behaviour • risk evidence", "ASSIST — NOT AUTOMATION");
        card("ASSIST", "ANVI answers • reports • maintenance intelligence", "HUMAN DECISION REQUIRED");

        Button live = new Button(this);
        live.setText("OPEN LIVE ANVIQO");
        live.setTextColor(BG);
        live.setTextSize(13);
        live.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        live.setOnClickListener(v -> openLive("ANVIQO"));
        content.addView(live, new LinearLayout.LayoutParams(-1, 54));

        content.addView(label("System boundary", 15, TEXT));
        card("PLC WRITE", "Automatic PLC commands are disabled.", "BLOCKED");
        card("SCADA CONTROL", "Automatic control is disabled.", "BLOCKED");
        card("HUMAN GOVERNANCE", "Recommendations require human decision.", "REQUIRED");
    }

    private void openLive(String section) {
        root.removeAllViews();
        LinearLayout top = new LinearLayout(this);
        top.setGravity(Gravity.CENTER_VERTICAL);
        top.setPadding(12, 10, 12, 10);
        top.setBackgroundColor(PANEL);
        Button back = new Button(this);
        back.setText("‹");
        back.setTextSize(22);
        back.setOnClickListener(v -> showHome());
        top.addView(back, new LinearLayout.LayoutParams(54, 54));
        top.addView(label("ANVIQO • " + section, 17, TEXT), new LinearLayout.LayoutParams(0, -2, 1));
        Button reload = new Button(this);
        reload.setText("↻");
        reload.setOnClickListener(v -> { if (webView != null) webView.reload(); });
        top.addView(reload, new LinearLayout.LayoutParams(54, 54));
        root.addView(top);

        webView = new WebView(this);
        WebSettings s = webView.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setSupportZoom(false);
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient());
        webView.loadUrl("https://anviqoai.com/");
        root.addView(webView, new LinearLayout.LayoutParams(-1, 0, 1));

        TextView safety = label("EVIDENCE FIRST • HUMAN GOVERNED • READ ONLY", 9, MUTED);
        safety.setGravity(Gravity.CENTER);
        root.addView(safety, new LinearLayout.LayoutParams(-1, 30));
    }

    @Override public void onBackPressed() {
        if (webView != null && webView.getParent() != null && webView.canGoBack()) {
            webView.goBack();
        } else {
            showHome();
        }
    }
}
