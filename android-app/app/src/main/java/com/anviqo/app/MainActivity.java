package com.anviqo.app;
import android.annotation.SuppressLint;
import android.app.Activity;
import android.os.Bundle;
import android.view.View;
import android.webkit.*;
public class MainActivity extends Activity {
 private WebView webView;
 @SuppressLint("SetJavaScriptEnabled") public void onCreate(Bundle b){
  super.onCreate(b); setContentView(com.anviqo.ai.mobile.R.layout.activity_main);
  webView=findViewById(com.anviqo.ai.mobile.R.id.webview);
  WebSettings s=webView.getSettings(); s.setJavaScriptEnabled(true); s.setDomStorageEnabled(true); s.setDatabaseEnabled(true); s.setSupportZoom(false); s.setBuiltInZoomControls(false);
  webView.setWebViewClient(new WebViewClient()); webView.setWebChromeClient(new WebChromeClient());
  final View p=findViewById(com.anviqo.ai.mobile.R.id.progress);
  webView.setWebViewClient(new WebViewClient(){public void onPageFinished(WebView v,String u){p.setVisibility(View.GONE);}});
  webView.loadUrl("https://anviqoai.com/");
 }
 @Override public void onBackPressed(){if(webView!=null&&webView.canGoBack())webView.goBack();else super.onBackPressed();}
}