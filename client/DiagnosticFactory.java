package com.supercell.moco.localtest;

import android.app.Activity;
import android.app.AppComponentFactory;
import android.app.Application;
import android.app.Service;
import android.content.BroadcastReceiver;
import android.content.ContentProvider;
import android.content.Intent;
import android.content.pm.ApplicationInfo;
import android.util.Log;
import java.io.File;
import android.os.Process;
import android.os.Bundle;
import android.view.WindowManager;

/** Loads local diagnostics before the original factory initializes its loader. */
public final class DiagnosticFactory extends AppComponentFactory {
    static {
        File diagnostics = new File("/data/user/0/com.supercell.moco.localtest/files/diagnostics");
        Log.i("MocoDiagnostic", "Diagnostic directory available: " + (diagnostics.mkdirs() || diagnostics.isDirectory()));
        File ready = new File(diagnostics, "bootstrap-ready-" + Process.myPid());
        if (ready.exists() && !ready.delete()) throw new ExceptionInInitializerError("Cannot reset local bootstrap marker");
        System.loadLibrary("gadget");
        if (!ready.isFile()) throw new ExceptionInInitializerError("Local bootstrap failed; client startup refused");
        Log.i("MocoDiagnostic", "Diagnostic library loaded before original factory");
    }

    private AppComponentFactory delegate;

    /** Keeps offline research running while recording protection diagnostics. */
    public static void recordOfflineProtectionReport(String report) {
        Log.i("MocoDiagnostic", "Offline protection report: " + report);
    }

    private AppComponentFactory original(ClassLoader cl) {
        if (delegate == null) {
            try {
                delegate = (AppComponentFactory) Class.forName(
                    "androidx.core.app.CoreComponentFactory", true, cl).newInstance();
            } catch (ReflectiveOperationException e) {
                throw new RuntimeException("Original component factory failed", e);
            }
        }
        return delegate;
    }

    @Override public ClassLoader instantiateClassLoader(ClassLoader cl, ApplicationInfo info) {
        return original(cl).instantiateClassLoader(cl, info);
    }
    @Override public Application instantiateApplication(ClassLoader cl, String name)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        Application application = original(cl).instantiateApplication(cl, name);
        application.registerActivityLifecycleCallbacks(new Application.ActivityLifecycleCallbacks() {
            private void keepTestScreenAwake(Activity activity) {
                activity.getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
            }
            @Override public void onActivityCreated(Activity activity, Bundle state) { keepTestScreenAwake(activity); }
            @Override public void onActivityResumed(Activity activity) { keepTestScreenAwake(activity); }
            @Override public void onActivityStarted(Activity activity) {}
            @Override public void onActivityPaused(Activity activity) {}
            @Override public void onActivityStopped(Activity activity) {}
            @Override public void onActivitySaveInstanceState(Activity activity, Bundle state) {}
            @Override public void onActivityDestroyed(Activity activity) {}
        });
        return application;
    }
    @Override public Activity instantiateActivity(ClassLoader cl, String name, Intent intent)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        return original(cl).instantiateActivity(cl, name, intent);
    }
    @Override public Service instantiateService(ClassLoader cl, String name, Intent intent)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        return original(cl).instantiateService(cl, name, intent);
    }
    @Override public BroadcastReceiver instantiateReceiver(ClassLoader cl, String name, Intent intent)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        return original(cl).instantiateReceiver(cl, name, intent);
    }
    @Override public ContentProvider instantiateProvider(ClassLoader cl, String name)
            throws InstantiationException, IllegalAccessException, ClassNotFoundException {
        return original(cl).instantiateProvider(cl, name);
    }
}
