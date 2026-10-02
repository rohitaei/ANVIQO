package com.anviqo.app;

import android.Manifest;
import android.app.Activity;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.graphics.Color;
import android.graphics.Typeface;
import android.os.Bundle;
import android.speech.RecognizerIntent;
import android.speech.SpeechRecognizer;
import android.speech.RecognitionListener;
import android.view.Gravity;
import android.view.View;
import android.webkit.CookieManager;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Button;
import android.widget.EditText;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import android.widget.Toast;

import org.json.JSONObject;

import java.io.BufferedReader;
import java.io.InputStreamReader;
import java.io.OutputStream;
import java.net.CookieHandler;
import java.net.CookieStore;
import java.net.HttpURLConnection;
import java.net.URI;
import java.net.URLEncoder;
import java.util.ArrayList;
import java.util.List;
import java.util.Locale;
import java.util.concurrent.ExecutorService;
import java.util.concurrent.Executors;

public class MainActivity extends Activity {
    private static final String BASE = "https://anviqo.onrender.com";
    private static final int BG = Color.rgb(5,11,19);
    private static final int PANEL = Color.rgb(11,22,37);
    private static final int PANEL2 = Color.rgb(15,29,47);
    private static final int TEXT = Color.rgb(239,246,252);
    private static final int MUTED = Color.rgb(145,164,185);
    private static final int CYAN = Color.rgb(54,215,232);
    private static final int GREEN = Color.rgb(73,230,161);
    private static final int USER = Color.rgb(27,49,73);

    private LinearLayout root, messages, chips;
    private ScrollView scroll;
    private EditText input;
    private TextView status, plant;
    private ExecutorService executor = Executors.newSingleThreadExecutor();
    private java.net.CookieManager cookieManager;
    private SpeechRecognizer speech;
    private boolean loggedIn = false;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        cookieManager = new java.net.CookieManager();
        CookieHandler.setDefault(cookieManager);
        showLogin();
    }

    private TextView tv(String s, float size, int color) {
        TextView t = new TextView(this);
        t.setText(s); t.setTextSize(size); t.setTextColor(color);
        t.setPadding(0,4,0,4);
        return t;
    }

    private Button button(String s, View.OnClickListener l) {
        Button b = new Button(this);
        b.setText(s); b.setTextColor(TEXT); b.setTextSize(12); b.setAllCaps(false);
        b.setOnClickListener(l);
        return b;
    }

    private void showLogin() {
        root = new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL);
        root.setGravity(Gravity.CENTER); root.setPadding(28,28,28,28); root.setBackgroundColor(BG);

        TextView logo = tv("ANVI", 38, CYAN); logo.setTypeface(Typeface.DEFAULT, Typeface.BOLD);
        logo.setGravity(Gravity.CENTER);
        root.addView(logo);
        TextView sub = tv("THINK • PREDICT • PROTECT\nIndustrial intelligence • human governed", 13, MUTED);
        sub.setGravity(Gravity.CENTER); root.addView(sub);

        EditText u = new EditText(this); u.setHint("Username"); u.setTextColor(TEXT); u.setHintTextColor(MUTED);
        root.addView(u, new LinearLayout.LayoutParams(-1,56));
        EditText p = new EditText(this); p.setHint("Password"); p.setTextColor(TEXT); p.setHintTextColor(MUTED);
        p.setInputType(0x81); root.addView(p, new LinearLayout.LayoutParams(-1,56));

        Button login = button("Sign in to ANVI", v -> {
            String user=u.getText().toString().trim(), pass=p.getText().toString();
            if(user.isEmpty() || pass.isEmpty()) { Toast.makeText(this,"Enter username and password",Toast.LENGTH_SHORT).show(); return; }
            login.setEnabled(false); statusText("Connecting to ANVIQO…");
            executor.execute(() -> {
                final String result = loginRequest(user, pass);
                runOnUiThread(() -> {
                    login.setEnabled(true);
                    if("OK".equals(result)) { loggedIn=true; showChat(); }
                    else Toast.makeText(this,result,Toast.LENGTH_LONG).show();
                });
            });
        });
        login.setBackgroundColor(CYAN); login.setTextColor(BG);
        root.addView(login, new LinearLayout.LayoutParams(-1,56));
        root.addView(tv("Secure session • read-only intelligence • no PLC/SCADA control",11,MUTED));
        setContentView(root);
    }

    private String loginRequest(String user, String pass) {
        try {
            HttpURLConnection c=(HttpURLConnection)new java.net.URL(BASE+"/login").openConnection();
            c.setRequestMethod("POST"); c.setDoOutput(true); c.setInstanceFollowRedirects(false);
            c.setRequestProperty("Content-Type","application/x-www-form-urlencoded");
            String body="username="+URLEncoder.encode(user,"UTF-8")+"&password="+URLEncoder.encode(pass,"UTF-8");
            try(OutputStream os=c.getOutputStream()){os.write(body.getBytes("UTF-8"));}
            int code=c.getResponseCode();
            if(code==302 || code==303) return "OK";
            return "Login failed ("+code+")";
        } catch(Exception e){ return "Connection failed: "+e.getMessage(); }
    }

    private void showChat() {
        root=new LinearLayout(this); root.setOrientation(LinearLayout.VERTICAL); root.setBackgroundColor(BG);
        LinearLayout header=new LinearLayout(this); header.setPadding(14,10,10,8); header.setGravity(Gravity.CENTER_VERTICAL); header.setBackgroundColor(PANEL);
        Button menu=button("☰",v->showModules()); menu.setTextSize(20);
        header.addView(menu,new LinearLayout.LayoutParams(52,52));
        LinearLayout ht=new LinearLayout(this); ht.setOrientation(LinearLayout.VERTICAL);
        TextView h=tv("ANVI",20,TEXT); h.setTypeface(Typeface.DEFAULT,Typeface.BOLD); ht.addView(h);
        plant=tv("Plant: selected session",10,MUTED); ht.addView(plant);
        header.addView(ht,new LinearLayout.LayoutParams(0,-2,1));
        status=tv("● ONLINE",11,GREEN); status.setTypeface(Typeface.DEFAULT,Typeface.BOLD); header.addView(status);
        Button fresh=button("＋",v->newChat()); fresh.setTextSize(22); header.addView(fresh,new LinearLayout.LayoutParams(52,52));
        root.addView(header);

        scroll=new ScrollView(this); messages=new LinearLayout(this); messages.setOrientation(LinearLayout.VERTICAL); messages.setPadding(14,18,14,14);
        scroll.addView(messages); root.addView(scroll,new LinearLayout.LayoutParams(-1,0,1));

        chips=new LinearLayout(this); chips.setOrientation(LinearLayout.HORIZONTAL); chips.setPadding(10,4,10,4);
        addChip("Plant health","What is the current plant health?");
        addChip("PT-303","What is the status of PT-303?");
        addChip("What changed","What changed recently?");
        addChip("Spare stock","How many spares of PT-303 are available?");
        ScrollView cs=new ScrollView(this); cs.setHorizontalScrollBarEnabled(false); cs.setHorizontalFadingEdgeEnabled(true); cs.addView(chips);
        root.addView(cs,new LinearLayout.LayoutParams(-1,52));

        LinearLayout composer=new LinearLayout(this); composer.setPadding(8,6,8,6); composer.setGravity(Gravity.CENTER_VERTICAL); composer.setBackgroundColor(PANEL2);
        input=new EditText(this); input.setHint("Ask ANVI about your plant…"); input.setHintTextColor(MUTED); input.setTextColor(TEXT); input.setTextSize(15); input.setSingleLine(false);
        composer.addView(input,new LinearLayout.LayoutParams(0,58,1));
        Button mic=button("🎙",v->startVoice()); mic.setTextSize(18); composer.addView(mic,new LinearLayout.LayoutParams(52,56));
        Button send=button("➤",v->sendCurrent()); send.setTextSize(20); send.setTextColor(CYAN); composer.addView(send,new LinearLayout.LayoutParams(52,56));
        root.addView(composer);
        TextView safety=tv("EVIDENCE FIRST • HUMAN GOVERNED • PLC WRITE BLOCKED • SCADA CONTROL BLOCKED",9,MUTED); safety.setGravity(Gravity.CENTER); root.addView(safety);
        setContentView(root);

        addMessage(false,"Hello. I am ANVI.\n\nAsk me about plant health, alarms, instruments, I/O, equipment, events, maintenance, spares, shift intelligence or management decisions.\n\nI use the existing ANVIQO intelligence layer and return evidence before recommendations.");
    }

    private void addChip(String label,String prompt){
        Button b=button(label,v->{input.setText(prompt);sendCurrent();}); b.setTextSize(11); chips.addView(b,new LinearLayout.LayoutParams(-2,46));
    }

    private void addMessage(boolean mine,String text){
        LinearLayout row=new LinearLayout(this); row.setGravity(mine?Gravity.RIGHT:Gravity.LEFT); row.setPadding(0,5,0,5);
        TextView b=tv(text,15,TEXT); b.setPadding(16,12,16,12); b.setBackgroundColor(mine?USER:PANEL);
        LinearLayout.LayoutParams p=new LinearLayout.LayoutParams((int)(getResources().getDisplayMetrics().widthPixels*0.86),-2); row.addView(b,p); messages.addView(row);
        scroll.post(()->scroll.fullScroll(View.FOCUS_DOWN));
    }

    private void sendCurrent(){ String q=input.getText().toString().trim(); if(q.isEmpty())return; input.setText(""); addMessage(true,q); addMessage(false,"ANVI is checking evidence…"); final int idx=messages.getChildCount()-1; executor.execute(()->{
        String ans=askRequest(q);
        runOnUiThread(()->{ messages.removeViewAt(idx); addMessage(false,ans); });
    }); }

    private String askRequest(String q){
        try{
            HttpURLConnection c=(HttpURLConnection)new java.net.URL(BASE+"/api/ask").openConnection();
            c.setRequestMethod("POST"); c.setDoOutput(true); c.setConnectTimeout(30000); c.setReadTimeout(60000);
            c.setRequestProperty("Content-Type","application/json; charset=UTF-8");
            JSONObject o=new JSONObject(); o.put("question",q);
            try(OutputStream os=c.getOutputStream()){os.write(o.toString().getBytes("UTF-8"));}
            int code=c.getResponseCode();
            BufferedReader br=new BufferedReader(new InputStreamReader(code>=400?c.getErrorStream():c.getInputStream(),"UTF-8"));
            StringBuilder sb=new StringBuilder(); String line; while((line=br.readLine())!=null)sb.append(line);
            if(code>=400)return "ANVI could not complete that request. Server status: "+code+"\n\nPlease check the selected plant/session.";
            JSONObject r=new JSONObject(sb.toString());
            String a=r.optString("answer",r.optString("response",sb.toString()));
            if(r.has("plant_id")) runOnUiThread(()->plant.setText("Plant: "+r.optString("plant_id")));
            return clean(a)+"\n\nEvidence: "+(r.optString("evidence_status","AVAILABLE"))+"\nSafety: PLC WRITE BLOCKED • SCADA CONTROL BLOCKED • HUMAN DECISION REQUIRED";
        }catch(Exception e){return "ANVI connection error. Please try again.\n\n"+e.getMessage();}
    }

    private String clean(String s){
        return s.replace("\\n","\n").replace("\\u0027","'");
    }

    private void newChat(){ messages.removeAllViews(); addMessage(false,"New ANVI conversation started. What would you like to investigate?"); }

    private void statusText(String s){ if(status!=null)status.setText(s); }

    private void showModules(){
        root.removeAllViews();
        LinearLayout page=new LinearLayout(this); page.setOrientation(LinearLayout.VERTICAL); page.setBackgroundColor(BG);
        LinearLayout top=new LinearLayout(this); top.setPadding(10,8,10,8); top.setGravity(Gravity.CENTER_VERTICAL); top.setBackgroundColor(PANEL);
        Button back=button("‹",v->showChat()); back.setTextSize(24); top.addView(back,new LinearLayout.LayoutParams(54,54));
        TextView t=tv("ANVI capabilities",20,TEXT); t.setTypeface(Typeface.DEFAULT,Typeface.BOLD); top.addView(t,new LinearLayout.LayoutParams(0,-2,1)); page.addView(top);
        ScrollView sv=new ScrollView(this); LinearLayout list=new LinearLayout(this); list.setOrientation(LinearLayout.VERTICAL); list.setPadding(14,14,14,30);
        String[][] items={
            {"Plant Intelligence","What is the current plant health and which areas need attention?"},
            {"Live Alarms & Events","Show active alarms and recent events."},
            {"Equipment Intelligence","Show equipment intelligence for PT-303."},
            {"Instrumentation / I/O","Show the verified I/O information for PT-303."},
            {"What Changed","What changed recently?"},
            {"Predictive Intelligence","What is the predicted condition of PT-303?"},
            {"Maintenance Intelligence","Give maintenance intelligence for PT-303."},
            {"Critical Spares","How many spares of PT-303 are available?"},
            {"Shift Intelligence","Prepare the current shift intelligence report."},
            {"HOD / Management","Give management decision intelligence for the selected plant."},
            {"Field Reports / Plant Memory","Show verified plant memory for PT-303."},
            {"Plant & User Management","Open the full ANVIQO management workspace."},
            {"System Status / Safety","Show system status and safety boundary."}
        };
        for(String[] it:items){
            LinearLayout card=new LinearLayout(this); card.setOrientation(LinearLayout.VERTICAL); card.setPadding(18,12,18,12); card.setBackgroundColor(PANEL);
            TextView n=tv(it[0],16,TEXT); n.setTypeface(Typeface.DEFAULT,Typeface.BOLD); card.addView(n); card.addView(tv("Ask ANVI",11,CYAN));
            card.setOnClickListener(v->{ if(it[0].startsWith("Plant & User")) showWorkspace(); else {showChat(); input.setText(it[1]); sendCurrent();}});
            LinearLayout.LayoutParams cp=new LinearLayout.LayoutParams(-1,-2); cp.setMargins(0,0,0,10); list.addView(card,cp);
        }
        sv.addView(list); page.addView(sv,new LinearLayout.LayoutParams(-1,0,1));
        TextView foot=tv("All capabilities remain evidence-first, read-only and human governed.",10,MUTED); foot.setGravity(Gravity.CENTER); page.addView(foot,new LinearLayout.LayoutParams(-1,40));
        setContentView(page);
    }

    private void showWorkspace(){
        LinearLayout r=new LinearLayout(this); r.setOrientation(LinearLayout.VERTICAL); r.setBackgroundColor(BG);
        LinearLayout top=new LinearLayout(this); top.setGravity(Gravity.CENTER_VERTICAL); top.setBackgroundColor(PANEL);
        Button b=button("‹",v->showModules()); b.setTextSize(24); top.addView(b,new LinearLayout.LayoutParams(54,54));
        top.addView(tv("ANVIQO • Plant & User Management",17,TEXT),new LinearLayout.LayoutParams(0,-2,1)); r.addView(top);
        WebView w=new WebView(this); WebSettings s=w.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setDatabaseEnabled(true);
        w.setWebViewClient(new WebViewClient());
        syncWebCookies();
        w.loadUrl(BASE+"/");
        r.addView(w,new LinearLayout.LayoutParams(-1,0,1));
        r.addView(tv("Admin workspace • existing ANVIQO controls • human governed",9,MUTED));
        setContentView(r);
    }

    private void syncWebCookies(){
        try{
            CookieStore store=cookieManager.getCookieStore();
            android.webkit.CookieManager wm=android.webkit.CookieManager.getInstance();
            for(java.net.HttpCookie c:store.getCookies()){
                wm.setCookie(BASE,c.getName()+"="+c.getValue()+"; Path=/; Secure; HttpOnly");
            }
            wm.flush();
        }catch(Exception ignored){}
    }

    private void startVoice(){
        if(android.os.Build.VERSION.SDK_INT>=23 && checkSelfPermission(Manifest.permission.RECORD_AUDIO)!=PackageManager.PERMISSION_GRANTED){
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO},42); return;
        }
        if(!SpeechRecognizer.isRecognitionAvailable(this)){Toast.makeText(this,"Voice recognition is not available on this device.",Toast.LENGTH_SHORT).show();return;}
        if(speech!=null)speech.destroy();
        speech=SpeechRecognizer.createSpeechRecognizer(this);
        speech.setRecognitionListener(new RecognitionListener(){
            public void onReadyForSpeech(Bundle b){status.setText("● LISTENING");}
            public void onBeginningOfSpeech(){ }
            public void onRmsChanged(float v){ }
            public void onBufferReceived(byte[] b){ }
            public void onEndOfSpeech(){status.setText("● ONLINE");}
            public void onError(int e){status.setText("● ONLINE");}
            public void onResults(Bundle b){ArrayList<String>a=b.getStringArrayList(SpeechRecognizer.RESULTS_RECOGNITION); if(a!=null&&!a.isEmpty()){input.setText(a.get(0));sendCurrent();}}
            public void onPartialResults(Bundle b){}
            public void onEvent(int a,Bundle b){}
        });
        Intent i=new Intent(RecognizerIntent.ACTION_RECOGNIZE_SPEECH); i.putExtra(RecognizerIntent.EXTRA_LANGUAGE_MODEL,RecognizerIntent.LANGUAGE_MODEL_FREE_FORM); i.putExtra(RecognizerIntent.EXTRA_LANGUAGE,Locale.getDefault());
        speech.startListening(i);
    }

    @Override protected void onDestroy(){if(speech!=null)speech.destroy();executor.shutdownNow();super.onDestroy();}
    @Override public void onBackPressed(){showChat();}
}
