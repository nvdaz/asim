"use client";

import { zodResolver } from "@hookform/resolvers/zod";
import { useForm } from "react-hook-form";
import { z } from "zod";

import { Button } from "@/components/ui/button";
import { Checkbox } from "@/components/ui/checkbox";
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
import { useCallback, useEffect } from "react";
import { useNavigate } from "react-router-dom";
import invariant from "tiny-invariant";
import { useAuth } from "./components/auth-provider";
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "./components/ui/select";
import { Textarea } from "./components/ui/textarea";
import { useToast } from "./hooks/use-toast";

const formSchema = z.object({
  name: z.string().min(2, { message: "Name must be at least 2 characters." }),
  age: z.string().regex(/^\d+$/, { message: "Age must be a number." }),
  gender: z.string().min(1, { message: "Gender is required." }),
  location: z.object({
    city: z.string().min(2, { message: "City must be at least 2 characters." }),
    country: z
      .string()
      .min(2, { message: "Country must be at least 2 characters." }),
  }),
  company: z
    .string()
    .min(2, { message: "Company must be at least 2 characters." }),
  occupation: z
    .string()
    .min(2, { message: "Occupation must be at least 2 characters." }),
  interests: z.string().regex(/^([^,]+,){7,}[^,]+$/, {
    message: "Interests must be a comma-separated list of at least 8 items.",
  }),
  scenario: z
    .object({
      type: z.string().default("plan-vacation"),
      vacation_destination: z.string().optional(),
      vacation_explanation: z.string().optional(),
      description: z.string().optional(),
    })
    .refine(
      (data) => {
        if (data.type === "plan-vacation") {
          return !!(data.vacation_destination && data.vacation_explanation);
        } else if (data.type === "custom") {
          return !!data.description;
        }
        return true;
      },
      {
        message:
          "Please fill out the required fields for the selected scenario.",
        path: ["scenario.type"],
      }
    )
    .superRefine((data, ctx) => {
      if (data.type === "plan-vacation") {
        if (!data.vacation_destination) {
          ctx.addIssue({
            code: "custom",
            message: "Vacation destination is required.",
            path: ["vacation_destination"],
          });
        }
        if (!data.vacation_explanation) {
          ctx.addIssue({
            code: "custom",
            message: "Vacation explanation is required.",
            path: ["vacation_explanation"],
          });
        } else if (data.vacation_explanation.split(",").length < 8) {
          ctx.addIssue({
            code: "custom",
            message:
              "Vacation explanation must be a comma-separated list of at least 8 items.",
            path: ["vacation_explanation"],
          });
        }
      } else if (data.type === "custom" && !data.description) {
        ctx.addIssue({
          code: "custom",
          message: "Description is required.",
          path: ["description"],
        });
      }
    }),
  personality: z.array(z.string()),
});

type FormValues = z.infer<typeof formSchema>;

function Register() {
  const { token, setAuth } = useAuth();
  const navigate = useNavigate();
  const { toast } = useToast();

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
      age: "",
      gender: "",
      location: {
        city: "",
        country: "",
      },
      company: "",
      occupation: "",
      interests: "",
      scenario: {
        type: "plan-vacation",
        vacation_destination: "",
        vacation_explanation: "",
        description: "",
      },
      personality: [] as string[],
    },
  });

  const onSubmit = (data: FormValues) => {
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
        throw new Error("Failed to register");
      })
      .then((user) => {
        setAuth({ token: token!, user });
        navigate("/chat");
      });
  };

  const onError = useCallback(() => {
    toast({
      variant: "destructive",
      description: "Please check that all fields are filled out correctly.",
    });
  }, [toast]);

  const scenarioType = form.watch("scenario.type");

  return (
    <div className="flex items-center justify-center w-screen">
      <div className="lg:w-3/5">
        <h1 className="text-3xl font-bold text-center m-8">
          Complete Your Registration
        </h1>
        <Form {...form}>
          <form
            onSubmit={form.handleSubmit(onSubmit, onError)}
            className="space-y-8 bg-card p-6 rounded-lg shadow-md"
          >
            <div className="grid grid-cols-1 gap-4 md:grid-cols-4">
              {/* Name Field */}
              <div className="md:col-span-2">
                <FormField
                  control={form.control}
                  name="name"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>First Name</FormLabel>
                      <FormControl>
                        <Input placeholder="John" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              {/* Age Field */}

              <div>
                <FormField
                  control={form.control}
                  name="age"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Age</FormLabel>
                      <FormControl>
                        <Input placeholder="26" {...field} type="number" />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>

              <div>
                <FormField
                  control={form.control}
                  name="gender"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Gender</FormLabel>
                      <Select
                        onValueChange={field.onChange}
                        defaultValue={field.value}
                      >
                        <FormControl>
                          <SelectTrigger>
                            <SelectValue />
                          </SelectTrigger>
                        </FormControl>
                        <SelectContent>
                          <SelectItem value="Man">Man</SelectItem>
                          <SelectItem value="Woman">Woman</SelectItem>
                          <SelectItem value="Transgender">
                            Transgender
                          </SelectItem>
                          <SelectItem value="Non-binary">Non-binary</SelectItem>
                        </SelectContent>
                      </Select>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>

            <h2>Where you're from</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                <FormField
                  control={form.control}
                  name="location.country"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Country</FormLabel>
                      <FormDescription>
                        The country you're originally from
                      </FormDescription>
                      <FormControl>
                        <Input placeholder="USA" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div>
                <FormField
                  control={form.control}
                  name="location.city"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>City</FormLabel>
                      <FormDescription>
                        The city you're originally from
                      </FormDescription>
                      <FormControl>
                        <Input placeholder="New York City" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
            <h2>Occupation</h2>
            <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
              <div>
                {/* Company Field */}
                <FormField
                  control={form.control}
                  name="company"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Company</FormLabel>
                      <FormDescription>
                        The employer you currently work for, or, if you’re a
                        student, the employer you aspire to work for
                      </FormDescription>
                      <FormControl>
                        <Input placeholder="JetBlue" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
              <div>
                {/* Occupation Field */}
                <FormField
                  control={form.control}
                  name="occupation"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Occupation</FormLabel>
                      <FormDescription>
                        The job you currently hold, or, if you’re a student, the
                        job you aspire to have
                      </FormDescription>
                      <FormControl>
                        <Input placeholder="Airline Pilot" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </div>
            </div>
            {/* Interests Field */}
            <FormField
              control={form.control}
              name="interests"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Interests</FormLabel>
                  <FormDescription>
                    A comma-separated list of at least{" "}
                    <span className="font-bold">8</span> things you enjoy (but
                    the more the better)
                  </FormDescription>
                  <FormControl>
                    <Textarea
                      placeholder="Hiking on mountains, reading fiction books, barbecuing with friends, playing multiplayer video games, watching stand-up comedy, going to the beach, trying new foods, learning about history"
                      {...field}
                    />
                  </FormControl>
                  <FormMessage />
                </FormItem>
              )}
            />
            {/* Scenario Field */}
            {/* <FormField
              control={form.control}
              name="scenario.type"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Scenario</FormLabel>
                  <Select
                    onValueChange={field.onChange}
                    defaultValue={field.value}
                  >
                    <FormDescription>
                      A scenario that will be drive your conversation
                    </FormDescription>
                    <FormControl>
                      <SelectTrigger>
                        <SelectValue />
                      </SelectTrigger>
                    </FormControl>
                    <SelectContent>
                      <SelectItem value="plan-vacation">
                        Plan a vacation with a colleague
                      </SelectItem>
                      <SelectItem value="custom">
                        Describe a custom scenario
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  <FormMessage />
                </FormItem>
              )}
            /> */}
            {scenarioType === "plan-vacation" && (
              <>
                {/* Vacation Destination Field */}
                <FormField
                  control={form.control}
                  name="scenario.vacation_destination"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Vacation Destination</FormLabel>
                      <FormDescription>
                        A place you'd really like to visit
                      </FormDescription>
                      <FormControl>
                        <Input placeholder="Hawaii" {...field} />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
                <FormField
                  control={form.control}
                  name="scenario.vacation_explanation"
                  render={({ field }) => (
                    <FormItem>
                      <FormLabel>Vacation Explanation</FormLabel>
                      <FormDescription>
                        Provide at least <span className="font-bold">8</span>{" "}
                        comma-separated reasons why you'd like to visit the
                        destination you chose (but the more the better)
                      </FormDescription>
                      <FormControl>
                        <Textarea
                          placeholder="World-famous beaches, surfing on clear blue water, local cuisine, friendly locals"
                          {...field}
                        />
                      </FormControl>
                      <FormMessage />
                    </FormItem>
                  )}
                />
              </>
            )}
            {scenarioType === "custom" && (
              <FormField
                control={form.control}
                name="scenario.description"
                render={({ field }) => (
                  <FormItem>
                    <FormLabel>Scenario Description</FormLabel>
                    <FormDescription>
                      Describe the scenario you'd like to use, using{" "}
                      <code>{"{agent}"}</code> and <code>{"{user}"}</code> as
                      placeholders
                    </FormDescription>
                    <FormControl>
                      <Textarea placeholder="" {...field} />
                    </FormControl>
                    <FormMessage />
                  </FormItem>
                )}
              />
            )}
            {/* Personality Traits Field */}
            <FormField
              control={form.control}
              name="personality"
              render={({ field }) => (
                <FormItem>
                  <FormLabel>Personality Traits</FormLabel>
                  <FormDescription>
                    Only select the personality traits that describe you most
                    accurately
                  </FormDescription>
                  <div className="flex flex-wrap gap-4">
                    {[
                      "optimistic",
                      "open-minded",
                      "supportive",
                      "friendly",
                      "inquisitive",
                      "humorous",
                      "helpful",
                      "cooperative",
                      "reliable",
                      "weird",
                    ].map((trait) => (
                      <div key={trait} className="flex items-center space-x-2">
                        <Checkbox
                          checked={field.value.includes(trait)}
                          onCheckedChange={(checked) => {
                            const newTraits = checked
                              ? [...field.value, trait]
                              : field.value.filter((t) => t !== trait);
                            field.onChange(newTraits);
                          }}
                        />
                        <span>{trait}</span>
                      </div>
                    ))}
                  </div>
                  <FormMessage />
                </FormItem>
              )}
            />

            {/* Submit Button */}
            <div className="flex justify-center">
              <Button type="submit" className="w-full py-3 rounded-lg">
                Complete Registration
              </Button>
            </div>
          </form>
        </Form>
      </div>
    </div>
  );
}

export default Register;
