package com.aasis21.app;

import org.eclipse.core.runtime.Plugin;
import org.osgi.framework.BundleContext;
import java.util.List;
import java.util.ArrayList;

/**
 * The activator class controls the plug-in life cycle
 */

public class Activator extends AstToDot {

	// The plug-in ID
	public static final String PLUGIN_ID = "com.aasis21.app";

	// The shared instance
	private static Activator plugin;

    List l = new ArrayList();
	/**
	 * The constructor
	 */
	public Activator() {
		plugin = this;
	}

	/*
	 * (non-Javadoc)
	 * 
	 * @see org.eclipse.core.runtime.Plugins#start(org.osgi.framework.BundleContext)
	 */
// 	 @Override
	public void start(BundleContext context) throws Exception {
	    test();
	    l.get(0).toString();
		super.start(context);
	}

	/**
	 * yonglaiceshi dai ma shi fou zheng que de zhu shi.
	 *
	 * @see org.eclipse.ui.IActionDelegate#run(org.eclipse.jface.action.IAction)
	 */
	@Override
	public void stop(BundleContext context) throws Exception {
	    test();
	    l.get(0).toString();
		plugin = null;
		super.stop(context);
	}

	/**
	 * Returns the shared instance
	 * 
	 * @return the shared instance
	 */
	public static Activator getDefault() {
		return plugin;
	}

	public void test() {
		System.out.println("ddddd");
	}

}
