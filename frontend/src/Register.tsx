"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import {
  Form,
  FormControl,
  FormDescription,
  FormField,
  FormItem,
  FormLabel,
  FormMessage,
} from "@/components/ui/form";
import { Input } from "@/components/ui/input";
import { useCallback, useEffect, useState } from "react";
import { useNavigate } from "react-router-dom";
import invariant from "tiny-invariant";
import { useAuth } from "./components/auth-provider";
import { useToast } from "./hooks/use-toast";
import { AnimatePresence } from "framer-motion";

const formSchema = z.object({
  name: z.string().min(2, { message: "Name must be at least 2 characters." }),
  pronouns: z
    .string()
    .min(2, { message: "Pronouns must be at least 2 characters." }),
  topic: z
    .string()
    .min(2, { message: "Topic chosen must be at least 2 characters." }),
});

type FormValues = z.infer<typeof formSchema>;

function Register() {
  const { token, setAuth } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();
  const [didSubmit, setDidSubmit] = useState(false);

  useEffect(() => {
    if (!token) {
      navigate("/");
    }
  });

  invariant(token);

  const form = useForm({
    resolver: zodResolver(formSchema),
    defaultValues: {
      name: "",
      pronouns: "",
      topic: "",
    },
  });

  const onSubmit = (data: FormValues) => {
    setDidSubmit(true);

    fetch(`${import.meta.env.VITE_API_URL}/auth/register`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${token}`,
      },
      body: JSON.stringify(data),
    })
      .then((res) => {
        if (res.ok) {
          return res.json();
        }

        throw new Error("Failed to register.");
      })
      .then((user) => {
        setAuth({ token: token!, user });
        navigate("/chat");
      })
      .catch(() => {
        setDidSubmit(false);
        toast({
          variant: "destructive",
          description: "An error occurred. Please try again.",
        });

        setDidSubmit(false);
      });
  };

  const onError = useCallback(() => {
    toast({
      variant: "destructive",
      description: "Please check that all fields are filled out correctly.",
    });
  }, [toast]);

  return (
    <div className="flex items-center justify-center w-screen">
      <div className="max-w-screen-sm">
        <h1 className="text-3xl font-semibold text-center mt-12 mb-8">
          Complete Your Registration
        </h1>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit, onError)}
            className="space-y-8 bg-card p-6 rounded-lg shadow-md"
          >
            <p className="text-gray-800 dark:text-gray-200">
              Please complete this form to finalize your registration. The
              information you provide will help us match you with a suitable
              conversation partner.
            </p>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
              {/* Name Field */}
              <div className="md:col-span-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>First Name</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              {/* Pronouns Field */}

              <div>
                <FormField
                  control={form.control}
                  name="pronouns"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Pronouns</FormLabel>
                      <FormControl>
                        <Input {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            {/* Topic Field */}
            <FormField
              control={form.control}
              name="topic"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Topic</FormLabel>
                  <FormDescription>
                    Something you're genuinely curious about, can engage in a
                    meaningful conversation about, and would like to explore
                    with a fellow enthusiast.
                  </FormDescription>
                  <FormControl>
                    <Input {...field} />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Submit Button */}
            <div className="flex justify-center flex-col items-center">
              <Button
                type="submit"
                className="w-full py-3 rounded-lg"
                disabled={didSubmit}
              >
                Complete Registration
              </Button>
              <AnimatePresence>
                {didSubmit && (
                  <p
                    key="submitting"
                    className="text-sm text-gray-500 mt-2 animate-pulse"
                  >
                    Submitting... Just a moment while we set up your account!
                  </p>
                )}
              </AnimatePresence>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
}

export default Register;
