package io.github.t92t1914.obscuricons;

import android.app.Activity;
import android.content.ComponentName;
import android.content.Intent;
import android.content.pm.ResolveInfo;
import android.graphics.Typeface;
import android.os.Bundle;
import android.util.Xml;
import android.view.View;
import android.view.WindowInsets;
import android.widget.Button;
import android.widget.LinearLayout;
import android.widget.ScrollView;
import android.widget.TextView;
import java.io.InputStream;
import java.util.ArrayList;
import java.util.Collections;
import java.util.HashSet;
import java.util.List;
import java.util.Set;
import org.json.JSONArray;
import org.json.JSONObject;
import org.xmlpull.v1.XmlPullParser;

/** A local explanation and explicit coverage check, with no background service. */
public final class IconPackActivity extends Activity {
    private TextView result;
    private Button check;
    private String completedReport;

    @Override public void onCreate(Bundle savedState) {
        super.onCreate(savedState);
        Object retainedReport = getLastNonConfigurationInstance();
        if (retainedReport instanceof String) completedReport = (String) retainedReport;
        final int padding = dp(24);
        ScrollView scroll = new ScrollView(this);
        scroll.setFillViewport(true);
        scroll.setBackgroundColor(getColor(R.color.iconpack_background));
        LinearLayout body = new LinearLayout(this);
        body.setOrientation(LinearLayout.VERTICAL);
        body.setBackgroundColor(getColor(R.color.iconpack_background));
        body.setPadding(padding, padding, padding, padding);
        body.setOnApplyWindowInsetsListener(new View.OnApplyWindowInsetsListener() {
            @Override public WindowInsets onApplyWindowInsets(View view, WindowInsets insets) {
                view.setPadding(padding + insets.getSystemWindowInsetLeft(),
                    padding + insets.getSystemWindowInsetTop(),
                    padding + insets.getSystemWindowInsetRight(),
                    padding + insets.getSystemWindowInsetBottom());
                return insets;
            }
        });
        addText(body, getString(R.string.app_name), 32, true);
        addText(body, getString(R.string.introduction), 18, false);
        addText(body, getString(R.string.versions), 14, false);
        addText(body, getString(R.string.instructions), 17, false);
        addText(body, getString(R.string.coverage_explanation), 15, false);
        check = new Button(this);
        check.setText(R.string.check_coverage);
        check.setAllCaps(false);
        body.addView(check);
        result = addText(body, completedReport == null
            ? getString(R.string.coverage_empty) : completedReport, 15, false);
        result.setTextIsSelectable(true);
        check.setOnClickListener(new View.OnClickListener() {
            @Override public void onClick(View view) {
                check.setEnabled(false);
                result.setText(R.string.checking);
                new Thread(new Runnable() {
                    @Override public void run() {
                        String report;
                        try {
                            report = coverageReport();
                        } catch (Exception error) {
                            report = null;
                        }
                        final String text = report;
                        runOnUiThread(new Runnable() {
                            @Override public void run() {
                                if (!isFinishing() && !isDestroyed()) {
                                    completedReport = text;
                                    result.setText(text == null ? getString(R.string.coverage_error) : text);
                                    check.setEnabled(true);
                                }
                            }
                        });
                    }
                }, "IconPackLocalCoverage").start();
            }
        });
        scroll.addView(body);
        setContentView(scroll);
        body.requestApplyInsets();
    }

    @Override public Object onRetainNonConfigurationInstance() {
        // Retain text only. No view, worker or serialized app inventory crosses recreation.
        return completedReport;
    }

    private int dp(int value) {
        return Math.round(value * getResources().getDisplayMetrics().density);
    }

    private TextView addText(LinearLayout body, String text, int size, boolean title) {
        TextView label = new TextView(this);
        label.setText(text);
        label.setTextColor(getColor(R.color.iconpack_foreground));
        label.setTextSize(size);
        label.setLineSpacing(dp(4), 1.0f);
        if (title) label.setTypeface(Typeface.create("sans-serif-medium", Typeface.NORMAL));
        LinearLayout.LayoutParams params = new LinearLayout.LayoutParams(
            LinearLayout.LayoutParams.MATCH_PARENT, LinearLayout.LayoutParams.WRAP_CONTENT);
        params.bottomMargin = dp(18);
        body.addView(label, params);
        return label;
    }

    private String coverageReport() throws Exception {
        Set<String> mapped = new HashSet<String>();
        try (InputStream stream = getAssets().open("appfilter.xml")) {
            XmlPullParser parser = Xml.newPullParser();
            parser.setInput(stream, "UTF-8");
            for (int event = parser.next(); event != XmlPullParser.END_DOCUMENT; event = parser.next()) {
                if (event == XmlPullParser.START_TAG && "item".equals(parser.getName())) {
                    String identity = parser.getAttributeValue(null, "component");
                    if (identity == null || !identity.startsWith("ComponentInfo{") || !identity.endsWith("}")) continue;
                    ComponentName component = ComponentName.unflattenFromString(
                        identity.substring(14, identity.length() - 1));
                    if (component != null) mapped.add(component.flattenToString());
                }
            }
        }
        byte[] catalogBytes;
        try (InputStream stream = getAssets().open("catalog.json")) {
            java.io.ByteArrayOutputStream output = new java.io.ByteArrayOutputStream();
            byte[] block = new byte[4096];
            for (int size; (size = stream.read(block)) != -1;) output.write(block, 0, size);
            catalogBytes = output.toByteArray();
        }
        JSONArray packages = new JSONObject(new String(catalogBytes, "UTF-8")).getJSONArray("packages");
        int visiblePackages = 0;
        int completePackages = 0;
        int visibleComponents = 0;
        int mappedComponents = 0;
        List<String> missing = new ArrayList<String>();
        for (int index = 0; index < packages.length(); index++) {
            JSONObject item = packages.getJSONObject(index);
            String packageName = item.getString("package");
            Intent query = new Intent(Intent.ACTION_MAIN).addCategory(Intent.CATEGORY_LAUNCHER).setPackage(packageName);
            List<ResolveInfo> entries = getPackageManager().queryIntentActivities(query, 0);
            Set<String> components = new HashSet<String>();
            for (ResolveInfo entry : entries) {
                if (entry.activityInfo != null && packageName.equals(entry.activityInfo.packageName)) {
                    components.add(new ComponentName(packageName, entry.activityInfo.name).flattenToString());
                }
            }
            if (components.isEmpty()) continue;
            visiblePackages++;
            boolean complete = true;
            for (String component : components) {
                visibleComponents++;
                if (mapped.contains(component)) {
                    mappedComponents++;
                } else {
                    complete = false;
                    missing.add(item.getString("label") + "\n" + component);
                }
            }
            if (complete) completePackages++;
        }
        Collections.sort(missing);
        StringBuilder report = new StringBuilder();
        report.append("Visible supported launcher apps: ").append(visiblePackages)
            .append("\nApps with all visible components mapped: ").append(completePackages)
            .append("\nMapped launcher components: ").append(mappedComponents).append(" / ").append(visibleComponents)
            .append("\n\nNo launcher entry was visible for ").append(packages.length() - visiblePackages)
            .append(" supported packages. They may be absent or have no visible launcher entry.")
            .append("\n\nThis is a local component comparison, not proof of Theme Park's applied result.");
        if (!missing.isEmpty()) {
            report.append("\n\nVisible components without an exact mapping:\n");
            for (String component : missing) report.append("\n").append(component).append("\n");
        }
        return report.toString();
    }
}
